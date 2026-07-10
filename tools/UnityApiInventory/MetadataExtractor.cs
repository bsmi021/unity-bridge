using System.Security.Cryptography;
using Mono.Cecil;

namespace UnityApiInventory;

internal static class MetadataExtractor
{
    public static ExtractionResult Extract(
        string path,
        string displayPath,
        InventoryOptions options,
        CaptureContext context,
        ProjectMetadataIndex projectMetadata)
    {
        using AssemblyDefinition definition = AssemblyDefinition.ReadAssembly(
            path,
            new ReaderParameters { InMemory = true, ReadingMode = ReadingMode.Deferred });
        ProvenanceInfo provenance = projectMetadata.Classify(
            path,
            definition.Name.Name,
            ProvenanceClassifier.Classify(path));
        var assembly = new AssemblyRecord(
            definition.Name.Name,
            displayPath,
            definition.MainModule.Mvid.ToString("D"),
            FileSha256(path),
            provenance);
        AvailabilityInfo availability = ProvenanceClassifier.Availability(provenance, options);
        var records = new List<ApiRecord>();
        AddForwarders(definition.MainModule, assembly, availability, context, records);
        foreach (TypeDefinition type in definition.MainModule.Types)
        {
            AddType(type, assembly, availability, context, records);
        }

        return new ExtractionResult(assembly, records);
    }

    private static void AddType(
        TypeDefinition type,
        AssemblyRecord assembly,
        AvailabilityInfo availability,
        CaptureContext context,
        List<ApiRecord> records)
    {
        if (!MetadataHelpers.IsPubliclyAccessible(type)) return;
        records.Add(TypeRecord(type, assembly, availability, context));
        HashSet<MethodDefinition> accessors = MetadataHelpers.Accessors(type);
        records.AddRange(type.Methods
            .Where(method => method.IsPublic && !accessors.Contains(method))
            .Select(method => MethodRecord(type, method, assembly, availability, context)));
        records.AddRange(type.Properties
            .Where(IsPublic)
            .Select(property => PropertyRecord(type, property, assembly, availability, context)));
        records.AddRange(type.Events
            .Where(IsPublic)
            .Select(item => EventRecord(type, item, assembly, availability, context)));
        records.AddRange(type.Fields
            .Where(field => field.IsPublic)
            .Select(field => FieldRecord(type, field, assembly, availability, context)));
        foreach (TypeDefinition nested in type.NestedTypes)
        {
            AddType(nested, assembly, availability, context, records);
        }
    }

    private static ApiRecord TypeRecord(
        TypeDefinition type,
        AssemblyRecord assembly,
        AvailabilityInfo availability,
        CaptureContext context)
    {
        string typeName = SignatureFormatter.DeclaringType(type);
        return Create(
            $"{assembly.Name}::T:{typeName}",
            $"{assembly.Name}::{typeName}",
            "type",
            "type",
            type,
            assembly,
            availability,
            context,
            typeKind: MetadataHelpers.TypeKind(type),
            declaringType: type.DeclaringType is null
                ? null
                : $"{assembly.Name}::{SignatureFormatter.DeclaringType(type.DeclaringType)}",
            isStatic: type.IsAbstract && type.IsSealed,
            genericArity: type.GenericParameters.Count);
    }

    private static ApiRecord MethodRecord(
        TypeDefinition type,
        MethodDefinition method,
        AssemblyRecord assembly,
        AvailabilityInfo availability,
        CaptureContext context)
    {
        string declaring = SignatureFormatter.DeclaringType(type);
        string name = SignatureFormatter.MethodName(method);
        string parameters = SignatureFormatter.Parameters(method.Parameters);
        string returnType = SignatureFormatter.Type(method.ReturnType);
        string identityReturn = method.Name is "op_Implicit" or "op_Explicit"
            ? $"->{returnType}"
            : string.Empty;
        return Create(
            $"{assembly.Name}::M:{declaring}.{name}({parameters}){identityReturn}",
            $"{assembly.Name}::{declaring}.{name}({parameters})->{returnType}",
            "member",
            method.IsConstructor ? "constructor" : "method",
            method,
            assembly,
            availability,
            context,
            declaringType: $"{assembly.Name}::{declaring}",
            isStatic: method.IsStatic,
            genericArity: method.GenericParameters.Count);
    }

    private static ApiRecord PropertyRecord(
        TypeDefinition type,
        PropertyDefinition property,
        AssemblyRecord assembly,
        AvailabilityInfo availability,
        CaptureContext context)
    {
        string declaring = SignatureFormatter.DeclaringType(type);
        string parameters = SignatureFormatter.Parameters(property.Parameters);
        string indexer = parameters.Length == 0 ? string.Empty : $"({parameters})";
        MethodDefinition? accessor = property.GetMethod ?? property.SetMethod;
        return Create(
            $"{assembly.Name}::P:{declaring}.{property.Name}{indexer}",
            $"{assembly.Name}::{declaring}.{property.Name}{indexer}:{SignatureFormatter.Type(property.PropertyType)}",
            "member",
            "property",
            property,
            assembly,
            availability,
            context,
            declaringType: $"{assembly.Name}::{declaring}",
            isStatic: accessor?.IsStatic ?? false);
    }

    private static ApiRecord EventRecord(
        TypeDefinition type,
        EventDefinition eventDefinition,
        AssemblyRecord assembly,
        AvailabilityInfo availability,
        CaptureContext context)
    {
        string declaring = SignatureFormatter.DeclaringType(type);
        MethodDefinition? accessor = eventDefinition.AddMethod ?? eventDefinition.RemoveMethod;
        return Create(
            $"{assembly.Name}::E:{declaring}.{eventDefinition.Name}",
            $"{assembly.Name}::{declaring}.{eventDefinition.Name}:{SignatureFormatter.Type(eventDefinition.EventType)}",
            "member",
            "event",
            eventDefinition,
            assembly,
            availability,
            context,
            declaringType: $"{assembly.Name}::{declaring}",
            isStatic: accessor?.IsStatic ?? false);
    }

    private static ApiRecord FieldRecord(
        TypeDefinition type,
        FieldDefinition field,
        AssemblyRecord assembly,
        AvailabilityInfo availability,
        CaptureContext context)
    {
        string declaring = SignatureFormatter.DeclaringType(type);
        return Create(
            $"{assembly.Name}::F:{declaring}.{field.Name}",
            $"{assembly.Name}::{declaring}.{field.Name}:{SignatureFormatter.Type(field.FieldType)}",
            "member",
            "field",
            field,
            assembly,
            availability,
            context,
            declaringType: $"{assembly.Name}::{declaring}",
            isStatic: field.IsStatic);
    }

    private static ApiRecord Create(
        string symbolId,
        string signature,
        string recordKind,
        string memberKind,
        Mono.Cecil.ICustomAttributeProvider provider,
        AssemblyRecord assembly,
        AvailabilityInfo availability,
        CaptureContext context,
        string? typeKind = null,
        string? declaringType = null,
        bool isStatic = false,
        int genericArity = 0)
    {
        return new ApiRecord
        {
            SymbolId = symbolId,
            CanonicalSignature = signature,
            RecordKind = recordKind,
            MemberKind = memberKind,
            TypeKind = typeKind,
            DeclaringType = declaringType,
            IsStatic = isStatic,
            GenericArity = genericArity,
            Obsolete = MetadataHelpers.Obsolete(provider),
            Availability = availability,
            Provenance = assembly.Provenance,
            Assembly = assembly,
            Context = context,
        };
    }

    private static void AddForwarders(
        ModuleDefinition module,
        AssemblyRecord assembly,
        AvailabilityInfo availability,
        CaptureContext context,
        List<ApiRecord> records)
    {
        foreach (ExportedType type in module.ExportedTypes.Where(MetadataHelpers.IsTypeForwarder))
        {
            string typeName = type.FullName.Replace('/', '+');
            records.Add(new ApiRecord
            {
                SymbolId = $"{assembly.Name}::TF:{typeName}",
                CanonicalSignature = $"{assembly.Name}::{typeName}",
                RecordKind = "type_forwarder",
                MemberKind = "type_forwarder",
                Obsolete = new ObsoleteInfo(false, null, false),
                Availability = availability,
                Provenance = assembly.Provenance,
                Assembly = assembly,
                Context = context,
            });
        }
    }

    private static bool IsPublic(PropertyDefinition property)
    {
        return property.GetMethod?.IsPublic is true || property.SetMethod?.IsPublic is true;
    }

    private static bool IsPublic(EventDefinition item)
    {
        return item.AddMethod?.IsPublic is true || item.RemoveMethod?.IsPublic is true;
    }

    private static string FileSha256(string path)
    {
        using FileStream stream = File.OpenRead(path);
        return Convert.ToHexString(SHA256.HashData(stream)).ToLowerInvariant();
    }
}

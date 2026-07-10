using Mono.Cecil;

namespace UnityApiInventory;

internal static class MetadataHelpers
{
    private const uint TypeForwarderFlag = 0x00200000;

    public static bool IsPubliclyAccessible(TypeDefinition type)
    {
        if (type.DeclaringType is null) return type.IsPublic;
        return type.IsNestedPublic && IsPubliclyAccessible(type.DeclaringType);
    }

    public static bool IsTypeForwarder(ExportedType type)
    {
        return ((uint)type.Attributes & TypeForwarderFlag) != 0;
    }

    public static string TypeKind(TypeDefinition type)
    {
        if (type.IsInterface) return "interface";
        if (type.IsEnum) return "enum";
        if (type.IsValueType) return "struct";
        if (type.BaseType?.FullName == "System.MulticastDelegate") return "delegate";
        return "class";
    }

    public static ObsoleteInfo Obsolete(Mono.Cecil.ICustomAttributeProvider provider)
    {
        CustomAttribute? attribute = provider.CustomAttributes.FirstOrDefault(
            item => item.AttributeType.FullName == "System.ObsoleteAttribute");
        if (attribute is null) return new ObsoleteInfo(false, null, false);

        string? message = attribute.ConstructorArguments.Count > 0
            ? attribute.ConstructorArguments[0].Value as string
            : null;
        bool isError = attribute.ConstructorArguments.Count > 1
            && attribute.ConstructorArguments[1].Value is true;
        return new ObsoleteInfo(true, message, isError);
    }

    public static HashSet<MethodDefinition> Accessors(TypeDefinition type)
    {
        var accessors = new HashSet<MethodDefinition>();
        foreach (PropertyDefinition property in type.Properties)
        {
            if (property.GetMethod is not null) accessors.Add(property.GetMethod);
            if (property.SetMethod is not null) accessors.Add(property.SetMethod);
            foreach (MethodDefinition method in property.OtherMethods) accessors.Add(method);
        }

        foreach (EventDefinition eventDefinition in type.Events)
        {
            if (eventDefinition.AddMethod is not null) accessors.Add(eventDefinition.AddMethod);
            if (eventDefinition.RemoveMethod is not null) accessors.Add(eventDefinition.RemoveMethod);
            if (eventDefinition.InvokeMethod is not null) accessors.Add(eventDefinition.InvokeMethod);
            foreach (MethodDefinition method in eventDefinition.OtherMethods) accessors.Add(method);
        }

        return accessors;
    }
}

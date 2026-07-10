using Mono.Cecil;

namespace UnityApiInventory;

internal static class SignatureFormatter
{
    public static string Type(TypeReference type)
    {
        return type switch
        {
            GenericParameter parameter => GenericParameter(parameter),
            GenericInstanceType instance => GenericInstance(instance),
            ArrayType array => Array(array),
            ByReferenceType reference => Type(reference.ElementType) + "&",
            PointerType pointer => Type(pointer.ElementType) + "*",
            OptionalModifierType optional => Type(optional.ElementType),
            RequiredModifierType required => Type(required.ElementType),
            PinnedType pinned => Type(pinned.ElementType),
            SentinelType sentinel => Type(sentinel.ElementType),
            FunctionPointerType function => FunctionPointer(function),
            _ => NormalizeName(type.FullName),
        };
    }

    public static string DeclaringType(TypeDefinition type) => NormalizeName(type.FullName);

    public static string MethodName(MethodDefinition method)
    {
        string suffix = method.GenericParameters.Count == 0
            ? string.Empty
            : $"``{method.GenericParameters.Count}";
        return method.Name + suffix;
    }

    public static string Parameters(IEnumerable<ParameterDefinition> parameters)
    {
        return string.Join(",", parameters.Select(parameter => Type(parameter.ParameterType)));
    }

    private static string GenericParameter(GenericParameter parameter)
    {
        string prefix = parameter.Type == GenericParameterType.Method ? "!!" : "!";
        return prefix + parameter.Position;
    }

    private static string GenericInstance(GenericInstanceType instance)
    {
        string arguments = string.Join(",", instance.GenericArguments.Select(Type));
        return $"{NormalizeName(instance.ElementType.FullName)}<{arguments}>";
    }

    private static string Array(ArrayType array)
    {
        string commas = new(',', Math.Max(0, array.Rank - 1));
        return $"{Type(array.ElementType)}[{commas}]";
    }

    private static string FunctionPointer(FunctionPointerType function)
    {
        string parameters = Parameters(function.Parameters);
        return $"fnptr({parameters})->{Type(function.ReturnType)}";
    }

    private static string NormalizeName(string name) => name.Replace('/', '+');
}

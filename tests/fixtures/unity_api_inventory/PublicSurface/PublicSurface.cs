using System;
using System.Runtime.CompilerServices;

[assembly: TypeForwardedTo(typeof(ForwardTarget.ForwardedApi))]

namespace FixtureApi;

public readonly struct ConversionValue
{
    public static implicit operator int(ConversionValue value) => 1;

    public static implicit operator string(ConversionValue value) => nameof(ConversionValue);
}

public class VisibleOuter
{
    public class VisibleNested
    {
        public event Action? Changed;

        public int Value { get; set; }

        public void Ping(int value) => Value = value;

        public void Ping(string value) => Value = value.Length;

        [Obsolete("Use Ping instead.", true)]
        public static string Legacy(string value) => value;

        public static T Echo<T>(ref T value) => value;

        public void RaiseChanged() => Changed?.Invoke();
    }

    internal class HiddenNested
    {
        public void LeakedMethod()
        {
        }
    }
}

internal class HiddenOuter
{
    public class PublicButUnreachable
    {
        public void LeakedMethod()
        {
        }
    }
}

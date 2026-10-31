using System;
using System.Collections.Generic;
using System.IO;

namespace UnityMobileKit.Tests
{
    /// <summary>
    /// Minimal, dependency-free test runner so the suite builds and runs offline with plain
    /// <c>dotnet run</c>. Each test gets a fresh scratch directory that is removed afterwards.
    /// </summary>
    public static class TestHarness
    {
        private static readonly List<(string Name, Action<string> Body)> Tests = new List<(string, Action<string>)>();

        public static void Add(string name, Action<string> body) => Tests.Add((name, body));

        public static int RunAll()
        {
            int passed = 0;
            var failures = new List<string>();

            foreach (var (name, body) in Tests)
            {
                string dir = Path.Combine(Path.GetTempPath(), "umk-tests", Guid.NewGuid().ToString("N"));
                Directory.CreateDirectory(dir);
                try
                {
                    body(dir);
                    passed++;
                    Console.WriteLine($"PASS  {name}");
                }
                catch (Exception e)
                {
                    failures.Add(name);
                    Console.WriteLine($"FAIL  {name}\n      {e.GetType().Name}: {e.Message}");
                }
                finally
                {
                    try { Directory.Delete(dir, recursive: true); } catch (IOException) { }
                }
            }

            Console.WriteLine();
            Console.WriteLine($"{passed}/{Tests.Count} passed, {failures.Count} failed.");
            return failures.Count == 0 ? 0 : 1;
        }
    }

    public sealed class AssertionException : Exception
    {
        public AssertionException(string message) : base(message) { }
    }

    public static class Assert
    {
        public static void True(bool condition, string message)
        {
            if (!condition) throw new AssertionException(message);
        }

        public static void Equal<T>(T expected, T actual, string what)
        {
            if (!EqualityComparer<T>.Default.Equals(expected, actual))
                throw new AssertionException($"{what}: expected <{expected}>, got <{actual}>");
        }

        public static void Near(double expected, double actual, double tolerance, string what)
        {
            if (Math.Abs(expected - actual) > tolerance)
                throw new AssertionException($"{what}: expected {expected} ± {tolerance}, got {actual}");
        }

        public static void Bytes(byte[] expected, byte[] actual, string what)
        {
            if (expected == null || actual == null)
            {
                if (expected != actual) throw new AssertionException($"{what}: one side is null");
                return;
            }
            if (expected.Length != actual.Length)
                throw new AssertionException($"{what}: length {expected.Length} vs {actual.Length}");
            for (int i = 0; i < expected.Length; i++)
            {
                if (expected[i] != actual[i])
                    throw new AssertionException($"{what}: differs at byte {i}");
            }
        }

        public static void Throws<TException>(Action action, string what) where TException : Exception
        {
            try
            {
                action();
            }
            catch (TException)
            {
                return;
            }
            catch (Exception e)
            {
                throw new AssertionException($"{what}: expected {typeof(TException).Name}, got {e.GetType().Name}");
            }
            throw new AssertionException($"{what}: expected {typeof(TException).Name}, nothing was thrown");
        }
    }
}

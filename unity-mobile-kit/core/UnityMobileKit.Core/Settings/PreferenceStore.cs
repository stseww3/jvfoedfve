using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace UnityMobileKit.Settings
{
    /// <summary>
    /// In-memory, typed key/value preferences (bool, int, float, string) with a compact text
    /// serialization. No I/O: <see cref="GameSettings"/> persists it through a save store.
    /// <para>
    /// A typed getter returns its default when the key is missing or holds another type, so a
    /// renamed or retyped preference degrades to its default instead of throwing.
    /// </para>
    /// </summary>
    public sealed class PreferenceStore
    {
        private const string Header = "UMK-PREF 1";

        private struct Entry
        {
            public char Type;
            public string Raw;
        }

        private readonly Dictionary<string, Entry> _entries = new Dictionary<string, Entry>(StringComparer.Ordinal);

        public int Count => _entries.Count;

        public IEnumerable<string> Keys => _entries.Keys;

        public bool ContainsKey(string key) => _entries.ContainsKey(ValidateKey(key));

        public bool Remove(string key) => _entries.Remove(ValidateKey(key));

        public void Clear() => _entries.Clear();

        public bool GetBool(string key, bool defaultValue = false)
        {
            return TryGetRaw(key, 'b', out string raw) ? raw == "1" : defaultValue;
        }

        public int GetInt(string key, int defaultValue = 0)
        {
            return TryGetRaw(key, 'i', out string raw)
                && int.TryParse(raw, NumberStyles.AllowLeadingSign, CultureInfo.InvariantCulture, out int value)
                ? value : defaultValue;
        }

        public float GetFloat(string key, float defaultValue = 0f)
        {
            return TryGetRaw(key, 'f', out string raw)
                && float.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out float value)
                ? value : defaultValue;
        }

        public string GetString(string key, string defaultValue = null)
        {
            return TryGetRaw(key, 's', out string raw) ? raw : defaultValue;
        }

        /// <summary>Returns true if the stored value changed.</summary>
        public bool SetBool(string key, bool value) => SetRaw(key, 'b', value ? "1" : "0");

        /// <summary>Returns true if the stored value changed.</summary>
        public bool SetInt(string key, int value) => SetRaw(key, 'i', value.ToString(CultureInfo.InvariantCulture));

        /// <summary>Returns true if the stored value changed. NaN and infinities are rejected.</summary>
        public bool SetFloat(string key, float value)
        {
            if (float.IsNaN(value) || float.IsInfinity(value))
            {
                throw new ArgumentOutOfRangeException(nameof(value), "Value must be a finite number.");
            }
            return SetRaw(key, 'f', value.ToString("R", CultureInfo.InvariantCulture));
        }

        /// <summary>Returns true if the stored value changed. Any text is allowed, including tabs and line breaks.</summary>
        public bool SetString(string key, string value)
        {
            if (value == null) throw new ArgumentNullException(nameof(value));
            return SetRaw(key, 's', value);
        }

        /// <summary>UTF-8 text, one entry per line, keys in ordinal order so identical contents give identical bytes.</summary>
        public byte[] Serialize()
        {
            var keys = new List<string>(_entries.Keys);
            keys.Sort(StringComparer.Ordinal);

            var sb = new StringBuilder();
            sb.Append(Header).Append('\n');
            foreach (string key in keys)
            {
                Entry entry = _entries[key];
                sb.Append(entry.Type).Append('\t');
                Escape(sb, key);
                sb.Append('\t');
                Escape(sb, entry.Raw);
                sb.Append('\n');
            }
            return Encoding.UTF8.GetBytes(sb.ToString());
        }

        /// <summary>
        /// Replaces the contents with serialized data. On malformed input the store is left
        /// unchanged and false is returned.
        /// </summary>
        public bool TryDeserialize(byte[] bytes)
        {
            if (bytes == null) return false;

            string text;
            try
            {
                text = new UTF8Encoding(false, true).GetString(bytes);
            }
            catch (ArgumentException)
            {
                return false;
            }

            string[] lines = text.Split('\n');
            if (lines[0] != Header) return false;

            var parsed = new Dictionary<string, Entry>(StringComparer.Ordinal);
            for (int i = 1; i < lines.Length; i++)
            {
                if (lines[i].Length == 0) continue;
                string[] fields = lines[i].Split('\t');
                if (fields.Length != 3 || fields[0].Length != 1) return false;
                char type = fields[0][0];
                if (!TryUnescape(fields[1], out string key) || !IsValidKey(key)) return false;
                if (!TryUnescape(fields[2], out string raw) || !IsValidRaw(type, raw)) return false;
                parsed[key] = new Entry { Type = type, Raw = raw };
            }

            _entries.Clear();
            foreach (var pair in parsed) _entries.Add(pair.Key, pair.Value);
            return true;
        }

        private static bool IsValidKey(string key)
        {
            return !string.IsNullOrEmpty(key) && key.IndexOfAny(new[] { '\t', '\n', '\r' }) < 0;
        }

        private static string ValidateKey(string key)
        {
            if (!IsValidKey(key))
            {
                throw new ArgumentException("Key must be non-empty and contain no tabs or line breaks.", nameof(key));
            }
            return key;
        }

        private bool TryGetRaw(string key, char type, out string raw)
        {
            if (_entries.TryGetValue(ValidateKey(key), out var entry) && entry.Type == type)
            {
                raw = entry.Raw;
                return true;
            }
            raw = null;
            return false;
        }

        private bool SetRaw(string key, char type, string raw)
        {
            ValidateKey(key);
            if (_entries.TryGetValue(key, out var existing) && existing.Type == type && existing.Raw == raw)
            {
                return false;
            }
            _entries[key] = new Entry { Type = type, Raw = raw };
            return true;
        }

        private static bool IsValidRaw(char type, string raw)
        {
            switch (type)
            {
                case 'b':
                    return raw == "0" || raw == "1";
                case 'i':
                    return int.TryParse(raw, NumberStyles.AllowLeadingSign, CultureInfo.InvariantCulture, out _);
                case 'f':
                    return float.TryParse(raw, NumberStyles.Float, CultureInfo.InvariantCulture, out float f)
                        && !float.IsNaN(f) && !float.IsInfinity(f);
                case 's':
                    return true;
                default:
                    return false;
            }
        }

        private static void Escape(StringBuilder sb, string value)
        {
            foreach (char c in value)
            {
                switch (c)
                {
                    case '\\': sb.Append("\\\\"); break;
                    case '\t': sb.Append("\\t"); break;
                    case '\n': sb.Append("\\n"); break;
                    case '\r': sb.Append("\\r"); break;
                    default: sb.Append(c); break;
                }
            }
        }

        private static bool TryUnescape(string value, out string result)
        {
            if (value.IndexOf('\\') < 0)
            {
                result = value;
                return true;
            }

            var sb = new StringBuilder(value.Length);
            for (int i = 0; i < value.Length; i++)
            {
                char c = value[i];
                if (c != '\\')
                {
                    sb.Append(c);
                    continue;
                }
                if (++i == value.Length)
                {
                    result = null;
                    return false;
                }
                switch (value[i])
                {
                    case '\\': sb.Append('\\'); break;
                    case 't': sb.Append('\t'); break;
                    case 'n': sb.Append('\n'); break;
                    case 'r': sb.Append('\r'); break;
                    default:
                        result = null;
                        return false;
                }
            }
            result = sb.ToString();
            return true;
        }
    }
}

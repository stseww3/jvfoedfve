using System;
using System.Collections.Generic;
using System.IO;
using Factory;

/// <summary>
/// Crash-safe atomic persistent storage provider for Android (Application.persistentDataPath).
/// Hardens LocalFileStorage against Android process kills / low-battery shutdowns during save writes:
///   1. Writes to "<filepath>.tmp" and flushes OS buffers to disk (FileStream.Flush(true)).
///   2. Preserves the previous valid file as "<filepath>.bak" before replacing "<filepath>".
///   3. During LoadAll(), ignores ".tmp" and ".bak" sidecar files and automatically falls back
///      to "<filepath>.bak" if the primary file is missing, empty, or fails storable parsing.
/// </summary>
public class AndroidAtomicFileStorage : LocalFileStorage
{
	[Dependency]
	private IHardwareCapabilities _androidHardware;

	[Dependency]
	private Diagnostics.StorageAuditTrail _androidAuditTrail;

	private const string TempExtension = ".tmp";
	private const string BackupExtension = ".bak";

	public override void LoadAll(Action loadCompleteCallback)
	{
		string rootPath = _androidHardware.PersistentStoragePath;
		if (Directory.Exists(rootPath))
		{
			RecoverOrCleanTempFiles(rootPath);
			string[] files = Directory.GetFiles(rootPath);
			foreach (string filepath in files)
			{
				if (filepath.EndsWith(TempExtension, StringComparison.OrdinalIgnoreCase) ||
				    filepath.EndsWith(BackupExtension, StringComparison.OrdinalIgnoreCase))
				{
					continue;
				}

				string fileName = Path.GetFileName(filepath);
				IStorableTypeHandler handler = _storableTypeHandlerRegistry.GetHandlerForFilename(fileName, out string playerId, out string deviceId);
				if (handler == null)
				{
					continue;
				}

				IStorable storable = TryLoadWithBackupFallback(filepath, handler);
				if (storable == null)
				{
					Log.Warn("Neither primary nor backup copy of {0} could be loaded.", fileName);
					continue;
				}

				storable.IsAuthoritative = true;
				if (handler.ProcessLoadedStorable(storable, playerId, deviceId))
				{
					if (deviceId == PlayerDatabase.LegacyDeviceId)
					{
						string newFilename = handler.GetFilename(playerId, _androidHardware.UniqueDeviceId);
						string destPath = Path.Combine(rootPath, newFilename);
						try
						{
							if (File.Exists(destPath))
							{
								File.Delete(filepath);
							}
							else
							{
								File.Move(filepath, destPath);
							}
						}
						catch (Exception ex)
						{
							Log.Warn("Failed to migrate legacy save file.\n{0}", ex);
						}
					}
				}
				else
				{
					_scope.Release(storable);
				}
			}
		}
		loadCompleteCallback?.Invoke();
	}

	public override bool Store(string filename, byte[] data, NamedStoreCompleted storeCompleteCallback)
	{
		string rootPath = _androidHardware.PersistentStoragePath;
		string filepath = Path.Combine(rootPath, filename);
		bool ok = AtomicWrite(filepath, data);
		StoreOperationResult result = ok ? StoreOperationResult.Succeeded : StoreOperationResult.Failed;
		storeCompleteCallback?.Invoke(filename, result);
		return ok;
	}

	public override bool Delete(string filename)
	{
		_androidAuditTrail?.RecordEvent("AndroidAtomicFileStorage.Delete", delegate(Dictionary<string, string> metadata)
		{
			metadata["filename"] = filename;
		});
		string filepath = Path.Combine(_androidHardware.PersistentStoragePath, filename);
		bool ok = true;
		try
		{
			if (File.Exists(filepath)) File.Delete(filepath);
			if (File.Exists(filepath + BackupExtension)) File.Delete(filepath + BackupExtension);
			if (File.Exists(filepath + TempExtension)) File.Delete(filepath + TempExtension);
		}
		catch (Exception ex)
		{
			Log.Warn("Unable to delete {0}.\n{1}", filepath, ex);
			ok = false;
		}
		return ok;
	}

	private static IStorable TryLoadWithBackupFallback(string filepath, IStorableTypeHandler handler)
	{
		byte[] primaryBytes = SafeReadBytes(filepath);
		if (primaryBytes != null && primaryBytes.Length > 0)
		{
			IStorable storable = handler.Load(primaryBytes);
			if (storable != null)
			{
				return storable;
			}
		}

		string bakPath = filepath + BackupExtension;
		byte[] bakBytes = SafeReadBytes(bakPath);
		if (bakBytes != null && bakBytes.Length > 0)
		{
			IStorable recovered = handler.Load(bakBytes);
			if (recovered != null)
			{
				try
				{
					File.Copy(bakPath, filepath, overwrite: true);
				}
				catch (Exception)
				{
				}
				return recovered;
			}
		}
		return null;
	}

	private static void RecoverOrCleanTempFiles(string rootPath)
	{
		try
		{
			string[] tempFiles = Directory.GetFiles(rootPath, "*" + TempExtension);
			foreach (string tmp in tempFiles)
			{
				string primary = tmp.Substring(0, tmp.Length - TempExtension.Length);
				try
				{
					if (!File.Exists(primary) && new FileInfo(tmp).Length > 0)
					{
						File.Move(tmp, primary);
					}
					else
					{
						File.Delete(tmp);
					}
				}
				catch (Exception)
				{
				}
			}
		}
		catch (Exception)
		{
		}
	}

	public static bool AtomicWrite(string filepath, byte[] data)
	{
		if (string.IsNullOrEmpty(filepath) || data == null)
		{
			return false;
		}
		string dir = Path.GetDirectoryName(filepath);
		string tmpPath = filepath + TempExtension;
		string bakPath = filepath + BackupExtension;
		try
		{
			if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
			{
				Directory.CreateDirectory(dir);
			}
			using (FileStream fs = new FileStream(tmpPath, FileMode.Create, FileAccess.Write, FileShare.None))
			{
				fs.Write(data, 0, data.Length);
				fs.Flush(flushToDisk: true);
			}
			if (File.Exists(filepath))
			{
				try
				{
					File.Copy(filepath, bakPath, overwrite: true);
				}
				catch (Exception)
				{
				}
				File.Delete(filepath);
			}
			File.Move(tmpPath, filepath);
			return true;
		}
		catch (Exception ex)
		{
			Log.Warn("AtomicWrite failed for {0}.\n{1}", filepath, ex);
			return false;
		}
	}

	private static byte[] SafeReadBytes(string filepath)
	{
		try
		{
			if (!File.Exists(filepath))
			{
				return null;
			}
			return File.ReadAllBytes(filepath);
		}
		catch (Exception)
		{
			return null;
		}
	}
}

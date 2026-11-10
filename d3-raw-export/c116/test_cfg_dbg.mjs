import fs from 'node:fs';
import path from 'node:path';

const ffDir = path.resolve('firefox_bin');
const dbgPath = path.resolve('ff_cfg_debug.log').replace(/\\/g, '\\\\');

const cfgCode = `// Mozilla AutoConfig
try {
  const { Services } = ChromeUtils.importESModule("resource://gre/modules/Services.sys.mjs");
  const { FileUtils } = ChromeUtils.importESModule("resource://gre/modules/FileUtils.sys.mjs");
  const f = new FileUtils.File("${dbgPath}");
  const fo = FileUtils.openFileOutputStream(f, FileUtils.MODE_WRONLY | FileUtils.MODE_CREATE | FileUtils.MODE_APPEND);
  const msg = "AutoConfig loaded in process type=" + Services.appinfo.processType + " at " + new Date().toISOString() + "\\n";
  fo.write(msg, msg.length);
  fo.close();
} catch (e) {}
`;

fs.writeFileSync(path.join(ffDir, 'firefox.cfg'), cfgCode, 'utf8');
console.log('Updated firefox.cfg with debug file write!');

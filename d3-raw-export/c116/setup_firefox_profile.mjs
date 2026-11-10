import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';

const profileDir = path.resolve('firefox_donor_9228');
fs.mkdirSync(profileDir, { recursive: true });

const userJs = `
user_pref("remote.active-protocols", 3);
user_pref("remote.events.async.wheel.enabled", true);
user_pref("browser.shell.checkDefaultBrowser", false);
user_pref("datareporting.policy.dataSubmissionEnabled", false);
user_pref("toolkit.telemetry.reportingpolicy.firstRun", false);
user_pref("browser.startup.homepage_override.mstone", "ignore");
user_pref("browser.aboutwelcome.enabled", false);
user_pref("trailhead.firstrun.didSeeAboutWelcome", true);
user_pref("focusmanager.testmode", true);
`;
fs.writeFileSync(path.join(profileDir, 'user.js'), userJs, 'utf8');
console.log('Created firefox_donor_9228/user.js');

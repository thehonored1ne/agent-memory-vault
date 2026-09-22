#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const { spawnSync } = require('child_process');

const args = process.argv.slice(2);
const command = args[0] || 'init';
const targetDir = process.cwd();
const packageRoot = path.resolve(__dirname, '..');
const vaultSourceDir = path.join(packageRoot, 'memory-vault');
const targetVaultDir = path.join(targetDir, 'memory-vault');
const agentsSourceFile = path.join(packageRoot, 'AGENTS.md');
const targetAgentsFile = path.join(targetDir, 'AGENTS.md');

function copyDirRecursive(src, dest) {
  if (!fs.existsSync(dest)) {
    fs.mkdirSync(dest, { recursive: true });
  }

  const entries = fs.readdirSync(src, { withFileTypes: true });
  for (const entry of entries) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);

    // Skip local database binaries
    if (entry.name === '.system' || entry.name === '__pycache__') {
      continue;
    }

    if (entry.isDirectory()) {
      copyDirRecursive(srcPath, destPath);
    } else {
      // Don't overwrite existing target files if they already exist
      if (!fs.existsSync(destPath)) {
        fs.copyFileSync(srcPath, destPath);
      }
    }
  }
}

function handleInit() {
  console.log('\n🧠 Initializing Agent Memory Vault in:', targetDir);

  // 1. Copy memory-vault directory
  if (path.resolve(vaultSourceDir) !== path.resolve(targetVaultDir)) {
    copyDirRecursive(vaultSourceDir, targetVaultDir);
    console.log('   ✓ Created memory-vault/ directory');
  }

  // 2. Safely handle AGENTS.md (non-destructive)
  if (path.resolve(packageRoot) !== path.resolve(targetDir)) {
    if (!fs.existsSync(targetAgentsFile)) {
      fs.copyFileSync(agentsSourceFile, targetAgentsFile);
      console.log('   ✓ Created AGENTS.md with Autonomous Memory Protocol');
    } else {
      const existing = fs.readFileSync(targetAgentsFile, 'utf-8');
      if (!existing.includes('Autonomous Agent Memory Protocol')) {
        const protocol = fs.readFileSync(agentsSourceFile, 'utf-8');
        fs.writeFileSync(targetAgentsFile, existing.trim() + '\n\n' + protocol, 'utf-8');
        console.log('   ✓ Appended Autonomous Memory Protocol to existing AGENTS.md');
      }
    }
  }

  // 3. Run python memory-vault/memory.py init
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
  const pyResult = spawnSync(pythonCmd, ['memory-vault/memory.py', 'init'], {
    cwd: targetDir,
    stdio: 'inherit',
    shell: true
  });

  if (pyResult.error) {
    console.warn(`\n[!] Notice: Could not automatically run '${pythonCmd}'. Ensure Python is installed.`);
    console.warn(`    To complete initialization, run: ${pythonCmd} memory-vault/memory.py init`);
  } else {
    console.log('\n🚀 Agent Memory Vault is ready!');
    console.log('   Your AI coding assistant will now autonomously ground itself and record learnings.');
  }
}

// Forward any other command directly to python engine
if (command === 'init') {
  handleInit();
} else {
  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3';
  const scriptPath = path.join(targetVaultDir, 'memory.py');

  if (fs.existsSync(scriptPath)) {
    spawnSync(pythonCmd, ['memory-vault/memory.py', ...args], {
      cwd: targetDir,
      stdio: 'inherit',
      shell: true
    });
  } else {
    console.error(`\n[!] Error: 'memory-vault/memory.py' not found in this folder.`);
    console.error(`    Run 'npx agent-memory-vault init' first to set up the vault.\n`);
    process.exit(1);
  }
}

const { spawn } = require('child_process');

/**
 * Custom script to handle the --catalog flag in package.json scripts.
 * Usage: node scripts/run-with-catalog.js <command> [args...] --catalog <catalog_name>
 * Example: npm run dev --catalog dev -> node scripts/run-with-catalog.js next dev --catalog dev
 */

const args = process.argv.slice(2);
let catalog = 'prod'; // Default catalog
const commandArgs = [];

for (let i = 0; i < args.length; i++) {
    if (args[i] === '--catalog' && i + 1 < args.length) {
        catalog = args[i + 1];
        i++; // Skip the next argument (catalog name)
    } else {
        commandArgs.push(args[i]);
    }
}

// Map short command aliases to full commands if needed
const command = commandArgs[0];
const remainingArgs = commandArgs.slice(1);

const nextCommands = new Set(['dev', 'build', 'start']);
const isNextCommand = nextCommands.has(command);
const fullCommand = isNextCommand ? 'next' : command;
const fullArgs = isNextCommand ? [command, ...remainingArgs] : remainingArgs;

console.log(`🚀 Using Databricks Catalog: ${catalog}`);

const child = spawn(fullCommand, fullArgs, {
    stdio: 'inherit',
    shell: true,
    env: {
        ...process.env,
        DATABRICKS_CATALOG: catalog,
    }
});

child.on('error', (err) => {
    console.error('Failed to start process:', err);
    process.exit(1);
});

child.on('exit', (code) => {
    process.exit(code);
});

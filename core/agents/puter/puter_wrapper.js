#!/usr/bin/env node
/**
 * Puter.js Wrapper for Python Agents
 * 
 * This script runs as a subprocess and provides a JSON-RPC like interface
 * over stdin/stdout for interacting with Puter.js.
 * 
 * Usage from Python:
 *   const { spawn } = require('child_process');
 *   const puter = spawn('node', ['path/to/puter_wrapper.js']);
 *   puter.stdin.write(JSON.stringify({action: 'chat', params: {messages: [...]}}) + '\n');
 *   // Then read stdout for response */
const path = require('path');

// Find the human-ai root directory by looking for known markers
function findHumanAiRoot() {
  let currentDir = __dirname;
  
  // Go up the directory tree until we find the human-ai root
  while (currentDir !== path.parse(currentDir).root) {
    // Check if this looks like the human-ai root
    const hasPackageJson = require('fs').existsSync(path.join(currentDir, 'package.json'));
    const hasCoreDir = require('fs').existsSync(path.join(currentDir, 'core'));
    const hasHumanAiInPath = currentDir.endsWith('human-ai') || currentDir.includes(path.sep + 'human-ai' + path.sep);
    
    if (hasPackageJson && hasCoreDir && hasHumanAiInPath) {
      return currentDir;
    }
    
    // Move up one directory
    const parentDir = path.dirname(currentDir);
    if (parentDir === currentDir) {
      // Reached filesystem root
      break;
    }
    currentDir = parentDir;
  }
  
  // Fallback: assume we're in human-ai/core/agents/puter and go up two levels
  return path.dirname(path.dirname(__dirname));
}

const humanAiDir = findHumanAiRoot();
const puterModulePath = path.join(humanAiDir, 'node_modules', '@heyputer', 'puter.js', 'src', 'index.js');

// Import Puter.js - the default export is the initialized Puter instance
const puterInstance = require(puterModulePath).default;

// Process a single request
async function processRequest(request) {
  try {
    let result;

    switch (request.action) {
      case 'initialize':
        result = { success: true, message: 'Puter.js already initialized' };
        break;

      case 'listModels':
        const models = await puterInstance.ai.listModels();
        result = { success: true, models };
        break;

      case 'listModelProviders':
        const providers = await puterInstance.ai.listModelProviders();
        result = { success: true, providers };
        break;

      case 'chat':
        const chatResponse = await puterInstance.ai.chat(request.params);
        result = { success: true, response: chatResponse };
        break;

      case 'txt2img':
        const imgResponse = await puterInstance.ai.txt2img(request.params);
        result = { success: true, response: imgResponse };
        break;

      case 'img2txt':
        const txtResponse = await puterInstance.ai.img2txt(request.params);
        result = { success: true, response: txtResponse };
        break;

      default:
        result = { success: false, error: `Unknown action: ${request.action}` };
    }

    return result;
  } catch (error) {
    return { success: false, error: error.message };
  }
}

// Main loop: read JSON lines from stdin, process, write JSON lines to stdout
const readline = require('readline');
const rl = readline.createInterface({
  input: process.stdin,
  output: process.stdout,
  terminal: false
});

rl.on('line', (line) => {
  try {
    const request = JSON.parse(line.trim());
    processRequest(request).then(response => {
      // Send response as JSON line
      console.log(JSON.stringify(response));
    });
  } catch (parseError) {
    console.log(JSON.stringify({ success: false, error: `Invalid JSON: ${parseError.message}` }));
  }
});

// Handle cleanup
process.on('SIGINT', () => {
  rl.close();
  process.exit(0);
});

process.on('SIGTERM', () => {
  rl.close();
  process.exit(0);
});
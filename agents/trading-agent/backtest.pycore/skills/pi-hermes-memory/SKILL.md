# pi-hermes-memory

Installs and manages the pi-hermes-memory npm package for enhanced memory capabilities in Hermes.

## Description

This skill provides utilities to install, configure, and use the pi-hermes-memory npm package, which enhances Hermes with persistent memory capabilities for better context retention and recall.

## Usage

Run the installation command to add pi-hermes-memory to your Hermes setup.

## Installation

```bash
pi install npm:pi-hermes-memory
```

## Configuration

After installation, configure the memory settings in your Hermes configuration file.

## Functions

- `install_hermes_memory()`: Installs the pi-hermes-memory package
- `configure_memory_size(size_mb)`: Sets the memory size limit
- `enable_persistent_storage(path)`: Enables persistent storage to disk
- `recall_context(query)`: Retrieves relevant context from memory
- `store_interaction(input, output)`: Stores an interaction in memory

## Example

```bash
# Install the package
pi install npm:pi-hermes-memory

# Configure in your Hermes setup
pi-hermes-memory configure --size 1024 --persistent ./hermes_memory.db
```

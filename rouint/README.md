# Rouint
A CLI-based API endpoint management and testing tool that wraps `curl`.

## Installation
```bash
pip install .
```

## Getting Started

### 1. Initialize Your Workspace
Create the local data directory where your endpoints and environments will be stored.
```bash
rouint init
```

### 2. Define Your Endpoints
Create reusable API request templates.
```bash
rouint add-new
```
*During creation, you can use placeholders like `{user_id}` in the path or query string.*

### 3. Fast-Track Testing
Quickly execute a saved request.
```bash
rouint start
```
*Flow: Select Endpoint $\rightarrow$ Enter Placeholder Values $\rightarrow$ Get Result.*

### 4. Manage Your API Collection
View, edit, or delete your saved endpoints.
```bash
rouint list
```
*Flow: View Table $\rightarrow$ Select Endpoint $\rightarrow$ (Edit / View / Delete).*

## Core Philosophy
Rouint is designed for developers who prefer the terminal. By wrapping `curl`, it provides the transparency of a raw shell command with the organization of a professional API client.

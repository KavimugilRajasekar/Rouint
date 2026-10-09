# User Guide

## Command Reference

### `rouint init`
Initializes the `.rouint-data` directory. Run this once per project.

### `rouint add-new`
Starts the interactive wizard to define a new endpoint.
- **Placeholders**: Use curly braces for dynamic values. 
  - Path: `/users/{id}`
  - Query: `/search?q={query}&page={p}`

### `rouint start`
The primary command for testing.
1. Select an endpoint from the list.
2. Provide values for any identified placeholders.
3. Review the result (Status, Time, Body).

### `rouint list`
The management hub for your endpoints.
- **Table View**: Displays a summary of all saved endpoints.
- **Actions**:
    - **Edit**: Change the name, method, path, or headers of an existing endpoint.
    - **View**: See the full JSON configuration.
    - **Delete**: Permanently remove an endpoint.

## Tips for Power Users
- **Base URLs**: Currently defaults to `http://localhost:8000`.
- **Headers**: Add custom headers like `Authorization` during the `add-new` or `Edit` process.
- **Bodies**: JSON bodies are supported for POST/PUT/PATCH methods.

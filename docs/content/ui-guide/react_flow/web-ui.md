# Using the Web-Based UI

FuncNodes provides a web-based UI for managing and visualizing workflows in an interactive and intuitive manner. This guide walks you through setting up and using the UI effectively.

---

## **Starting the Web UI**

To start the web UI, ensure you have FuncNodes installed and then run:

```bash
funcnodes runserver
```

This will start the FuncNodes server, and you can access the UI by navigating to:

```bash
http://localhost:8000
```

---

## **UI Features**

### **1️⃣ Workflow Editor**

- Drag-and-drop interface for creating workflows.
- Connect nodes visually to define execution flow.
- Edit node properties directly in the UI.

### **2️⃣ Node Configuration**

- Click on a node to modify its parameters.
- Supports custom inputs and outputs.
- Dynamic validation and live updates.

### **3️⃣ Execution Monitoring**

- Start, stop, and debug workflows.
- Real-time status updates for node execution.
- View logs and error messages directly in the UI.

### **4️⃣ Saving & Loading Workflows**

- Save workflows as JSON configurations.
- Load previously saved workflows.
- Export workflows for sharing or deployment.

---

## **Advanced Configuration**

### **Customizing the UI Port**

By default, the UI runs on port `8000`. To change this:

```bash
funcnodes runserver --port 8080
```

### **Securing the Web UI**

To enable authentication or SSL, modify the FuncNodes configuration file at:

```bash
~/.funcnodes/config.json
```

Add:

```json
{
  "frontend": {
    "host": "0.0.0.0",
    "port": 8000,
    "ssl": true
  }
}
```

---

## **What You Might Need to Add**

- **User Authentication**: If access control is required, add login functionality.
- **API Integration**: Document how to interact with the UI programmatically.
- **Custom Themes**: Explain how to modify the UI styling.
- **Performance Optimization**: Guide on handling large workflows efficiently.
- **Deployment Guide**: Steps to host the UI on a remote server.

For more details, visit the [FuncNodes GitHub repository](https://github.com/Linkdlab/funcnodes).

```



```

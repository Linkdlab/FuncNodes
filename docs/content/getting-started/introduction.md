# Understanding the Working Principles of FuncNodes

FuncNodes is a modular workflow automation framework designed to handle complex tasks using **node-based execution**. It enables users to construct workflows by interconnecting nodes, where each node represents an individual computational function. This guide provides a high-level overview of how FuncNodes operates internally.

---

## Core Concepts

### Nodes

- The fundamental building blocks of FuncNodes.
- Each node encapsulates a function with defined **inputs** and **outputs**.
- Nodes execute when all required inputs are available, producing output data for downstream nodes.
- Nodes are **extremly** easy to create, simply but a decorator to a existing function and the corresponding Node is created with the correct inputs and outputs automatically.

### Node Connections & Data Flow

- Nodes are connected via **inputs and outputs**, forming a **directed acyclic graph (DAG)**.
- Data flows from one node’s output to another’s input, **triggering execution dynamically**.

### Workers & Execution Environments

- Nodes execute inside **Workers**, which are isolated execution units.
- Workers ensure that processes are sandboxed, preventing conflicts between workflows.
- Each worker can run on its own virtual environment, ensuring dependency isolation.

### Workermanager

- The **Workermanager** orchestrates multiple workers.
- Manages worker lifecycle, logging, and monitoring.

### Event-Driven Execution

- FuncNodes follows an **event-driven model**, where each input change triggers execution.
- Execution order is determined dynamically based on data dependencies.
- Nodes can be triggered **synchronously or asynchronously** depending on their function.

---

## Execution Lifecycle

### Workflow Initialization

- Users define a workflow by arranging nodes and connecting them.
- The workflow is loaded into a Worker, ready for execution.

### Input Handling & Triggering

- When an input value changes, the connected node is **triggered**.
- If all required inputs are available, the node executes its function.

## Processing & Data Flow

- The node processes its input, generating output values.
- These outputs are passed to the connected nodes, potentially triggering their execution.

## Asynchronous & Parallel Execution

- Multiple nodes can execute in parallel if they don’t have data dependencies.
- Workers manage parallelism and ensure optimized execution.

## Logging & Debugging

- Execution logs are collected in real-time, allowing users to debug workflows.
- Users can monitor execution status and the underlying data through the **FuncNodes Web UI**.

---

## **Key Features that Enable Efficient Processing**

- **Modular Architecture** – Nodes can be customized and extended via plugins.
- **Web-Based UI** – Graphical workflow editor for easy management.
- **Event-Driven Execution** – Nodes trigger dynamically based on data changes.
- **Python & API Integration** – Supports Python-based functions and external API calls.

---

## **Example Use Case: Image Processing Pipeline**

![cat example](../examples/cat.png)

The live data preview of FuncNodes comes of course especially handy when working with visual data like images. In this example, we demonstrate how FuncNodes can be used to create an image processing pipeline. Each node performs a specific operation on the input image, color space conversion, blurring area detection, filtering and finally the output. Basically we create a grey-scale image of the image except, in this case where the cat has red fur.

You can see that every node shown a live preview of the current state of the image Inputs can be dynamically changed and are rendered depending on the underlying data type (e.g. numeric inputs are rendered as sliders when defined with a minimum and maximum).

---

## **Next Steps**

- Learn more about **[Nodes and their Configuration](../components/node.md)**.
- Explore **[How Inputs and Outputs Work](../components/inputs-outputs.md)**.
- Set up your first workflow with **[Basic Usage Guide](basic_usage.md)**.

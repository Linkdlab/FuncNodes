from funcnodes.worker.websocket import WSWorker


def main():
    worker = WSWorker(data_path="data", host="127.0.0.1", port=9382)
    worker.add_shelf_by_module(module="funcnodes.basic_nodes.math")
    worker.add_shelf_by_module(module="funcnodes.basic_nodes.logic")
    worker.add_shelf_by_module(module="funcnodes.basic_nodes.frontend")
    worker.run_forever()


if __name__ == "__main__":
    main()

import http.server
import socketserver
import webbrowser
import os
import time
import threading
import funcnodes as fn
import asyncio

PORT = 8000


class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/workermanager":
            self.get_worker_manager()
        else:
            # Call the superclass method to handle standard requests
            super().do_GET()

    def do_POST(self):
        if self.path == "/custom-post":
            self.handle_custom_post()
        else:
            # Send a 405 Method Not Allowed response for unsupported endpoints
            self.send_error(405, "Method Not Allowed")

    def get_worker_manager(self):
        # Implement custom GET handling logic here
        self.send_response(200)
        self.send_header("Content-type", "text/json")
        self.end_headers()
        self.wfile.write(
            f"ws://{fn.config.CONFIG['worker_manager']['host']}:{fn.config.CONFIG['worker_manager']['port']}".encode(
                "utf-8"
            )
        )

    def handle_custom_post(self):
        # Implement custom POST handling logic here
        content_length = int(self.headers["Content-Length"])
        post_data = self.rfile.read(content_length)

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        response = f"Received POST data: {post_data.decode('utf-8')}"
        self.wfile.write(response.encode("utf-8"))


class GracefulHTTPServer(socketserver.TCPServer):
    allow_reuse_address = False
    timeout = 5

    def __init__(self, server_address, RequestHandlerClass, bind_and_activate=True):
        super().__init__(server_address, RequestHandlerClass, bind_and_activate)
        self._is_serving = True

    def serve_forever(self, poll_interval=0.5):
        while self._is_serving:
            self.handle_request()

    def shutdown(self):
        self._is_serving = False


def _open_browser(port, delay=1.0):

    time.sleep(delay)
    webbrowser.open(f"http://localhost:{port}/index.html")


def run_server(port=PORT, open_browser=True):
    asyncio.run(fn.worker.worker_manager.assert_worker_manager_running())
    try:
        script_directory = os.path.dirname(os.path.abspath(__file__))
        os.chdir(script_directory)
        httpd = GracefulHTTPServer(("", port), CustomHTTPRequestHandler)
        print(f"Serving at port {port}")
        if open_browser:
            threading.Thread(target=_open_browser, args=(port,), daemon=True).start()
        httpd.serve_forever()
    except KeyboardInterrupt:
        if httpd._is_serving:
            print("Stopping server...")
            httpd.shutdown()
            print("Server has been stopped.")
        else:
            raise
    except OSError as e:
        print(f"Could not start server at port {port}: {e}")

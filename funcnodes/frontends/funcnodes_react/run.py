import http.server
import socketserver
import webbrowser
import threading
import os

PORT = 8000  # You can choose any available port

# Define the handler to serve files from the current directory
Handler = http.server.SimpleHTTPRequestHandler


# Launch the server in a new thread
def launch_server(port=PORT):
    script_directory = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_directory)
    with socketserver.TCPServer(("", port), Handler) as httpd:
        print(f"Serving at port {port}")
        httpd.serve_forever()


def run_server(port=PORT):
    server_thread = threading.Thread(target=launch_server, kwargs={"port": port})
    server_thread.daemon = (
        True  # This ensures the thread exits when the main program does
    )
    server_thread.start()

    # Open the default web browser to the server's address
    webbrowser.open(f"http://localhost:{PORT}/index.html")

    # Keep the script running while the server is serving
    try:
        server_thread.join()
    except KeyboardInterrupt:
        print("Server stopped by user")

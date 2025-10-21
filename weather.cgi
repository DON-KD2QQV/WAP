#!/usr/bin/python3
try:
    import sys, os

    # Patch sys.stdin to binary mode for Python 3 CGI
    if hasattr(sys.stdin, "buffer"):
        sys.stdin = sys.stdin.buffer

    def log_error(msg):
        with open(os.path.join(os.path.dirname(__file__), "cgi_error.log"), "a") as f:
            f.write(msg + "\n")

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'site-packages'))

    # Patch sys.stdout.write for flup compatibility
    if hasattr(sys.stdout, "buffer"):
        orig_write = sys.stdout.write
        def write_patched(data):
            if isinstance(data, bytes):
                data = data.decode('utf-8')
            return orig_write(data)
        sys.stdout.write = write_patched

    from flup.server.cgi import WSGIServer
    from app import app

    if __name__ == '__main__':
        WSGIServer(app).run()

except Exception as e:
    import traceback, os
    with open(os.path.join(os.path.dirname(__file__), "cgi_error.log"), "a") as f:
        f.write(traceback.format_exc() + "\n")
    print("Content-Type: text/plain\n")
    print("Internal Server Error. See cgi_error.log for details.")
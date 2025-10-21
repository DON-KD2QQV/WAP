#!/usr/bin/python3
try:
    import sys, os

    # Add site-packages to sys.path
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

    def simple_app(environ, start_response):
        start_response('200 OK', [('Content-Type', 'text/plain')])
        return [b"Hello from Flask+flup test!"]

    if __name__ == '__main__':
        WSGIServer(simple_app).run()

except Exception as e:
    import traceback
    print("Content-Type: text/plain\n")
    print("sys.path:", sys.path)
    print("site-packages contents:", os.listdir(os.path.join(os.path.dirname(__file__), 'site-packages')))
    print(traceback.format_exc())
def command(func):
    # ...existing code...
    func.name = func.__name__
    func.command = func
    return func

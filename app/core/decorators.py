

def public(func):
    func._is_public = True
    return func

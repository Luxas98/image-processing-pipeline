def conditional_decorator(dec, flag):
    def decorate(fn):
        return dec(fn) if flag else fn

    return decorate
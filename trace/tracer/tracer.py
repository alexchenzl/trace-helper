import os


def load_tracer(tracer):
    if tracer is None or tracer == '':
        return None
    with open(os.path.dirname(os.path.abspath(__file__)) + '/' + tracer + '.js', 'r') as f:
        content = f.read()
        # 'var temp = ' is added to avoid IDE reports error for convenience, need to be removed before executing it
        content = content.replace('var temp = ', '')
        return content

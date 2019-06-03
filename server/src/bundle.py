# call this file to  create the web output index.html that contains script and components
# this is written for this specific app and not ready to be used on other projects due to
# the lack of:
# 1. support for using require and module.exports statements
# 2. detecting link attributes of index.html
import json
import os

def bundle(index_file='../static/index.html',
        output_file='../static/bundle.html',
        components_dir='../static/components/'):
    """creates a bundle.html file that contains
    all the components, accessible from your
    script by for example using components.slider
    
    this is a string, so you need to put it
    into the innerHTML of some other element
    for it to render."""

    output = ''

    output += '<script>\nconst components = '

    # input
    components = {}

    """don't put components['components/dir/baz/bla.html'],
    put components.dir.baz.bla"""
    def build_tree(path, value, child=components):
        if os.sep in path:
            # the directory that contains files or folders, e.g. dir/baz
            parent_dir = path[:path.find(os.sep)]
            # the string containing the remaining path, e.g. baz/bla.html
            remaining = path[path.find(os.sep) + 1:]
            if not parent_dir in child:
                child[parent_dir] = {}
            build_tree(remaining, value, child[parent_dir])
        else:
            if '.' in path:
                path = path[:path.rfind('.')]
            child[path] = value

    # walk over all files that should be imported
    # and create a python dict containing their contents
    # like a folder structure
    for root, _, files in os.walk(components_dir):
        for filename in files:
            path = os.path.join(root, filename)
            with open(path, 'r') as f:
                # don't include the root dir that every component has in common
                path = path[len(components_dir):]
                build_tree(path, f.read())

    output += json.dumps(components)
    output += '\n</script>\n'

    with open(index_file, 'r') as f:
        output += f.read()
        
    # output
    with open(output_file, 'w+') as f:
        f.write(output)

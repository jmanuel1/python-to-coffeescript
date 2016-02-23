#!/usr/bin/env python
'''
This script makes a coffeescript file for every python source file listed
on the command line (wildcard file names are supported).

For full details, see README.md.

Released under the MIT Licence.

Written by Edward K. Ream.
'''
# All parts of this script are distributed under the following copyright. This is intended to be the same as the MIT license, namely that this script is absolutely free, even for commercial use, including resale. There is no GNU-like "copyleft" restriction. This license is compatible with the GPL.
# 
# **Copyright 2016 by Edward K. Ream. All Rights Reserved.**
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
# 
# **THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.**
import ast
import glob
import optparse
import os
import sys
import time
import token as token_module
import tokenize
import types
try:
    import ConfigParser as configparser # Python 2
except ImportError:
    import configparser # Python 3
try:
    import StringIO as io # Python 2
except ImportError:
    import io # Python 3
isPython3 = sys.version_info >= (3, 0, 0)

def main():
    '''
    The driver for the stand-alone version of make-stub-files.
    All options come from ~/stubs/make_stub_files.cfg.
    '''
    # g.cls()
    controller = MakeCoffeeScriptController()
    controller.scan_command_line()
    controller.scan_options()
    controller.run()
    print('done')

#
# Utility functions...
#

def dump(title, s=None):
    if s:
        print('===== %s...\n%s\n' % (title, s.rstrip()))
    else:
        print('===== %s...\n' % title)

def dump_dict(title, d):
    '''Dump a dictionary with a header.'''
    dump(title)
    for z in sorted(d):
        print('%30s %s' % (z, d.get(z)))
    print('')

def dump_list(title, aList):
    '''Dump a list with a header.'''
    dump(title)
    for z in aList:
        print(z)
    print('')

def pdb(self):
    '''Invoke a debugger during unit testing.'''
    try:
        import leo.core.leoGlobals as leo_g
        leo_g.pdb()
    except ImportError:
        import pdb
        pdb.set_trace()

def truncate(s, n):
    '''Return s truncated to n characters.'''
    return s if len(s) <= n else s[:n-3] + '...'


class CoffeeScriptTraverser(object):
    '''A class to convert python sources to coffeescript sources.'''
    # pylint: disable=consider-using-enumerate

    def __init__(self, controller):
        '''Ctor for CoffeeScriptFormatter class.'''
        self.controller = controller
        self.class_stack = []
        # Redirection. Set in format.
        self.sync_string = None
        self.leading_lines = None
        self.leading_string = None
        self.trailing_comment = None
        

    def format(self, node, s, tokens):
        '''Format the node (or list of nodes) and its descendants.'''
        self.level = 0
        sync = TokenSync(s, tokens)
        self.sync_string = sync.sync_string
        self.leading_lines = sync.leading_lines
        self.leading_string = sync.leading_string
        self.trailing_comment = sync.trailing_comment
        val = self.visit(node)
        return val or ''

    def indent(self, s):
        '''Return s, properly indented.'''
        # assert not s.startswith('\n'), (g.callers(), repr(s))
        n = 0
        while s and s.startswith('\n'):
            n += 1
            s = s[1:]
        return '%s%s%s' % ('\n' * n, ' ' * 4 * self.level, s)

    def visit(self, node):
        '''Return the formatted version of an Ast node, or list of Ast nodes.'''
        name = node.__class__.__name__
        if isinstance(node, (list, tuple)):
            return ', '.join([self.visit(z) for z in node])
        elif node is None:
            return 'None'
        else:
            assert isinstance(node, ast.AST), name
            method = getattr(self, 'do_' + name)
            s = method(node)
            if isPython3:
                assert isinstance(s, str)
            else:
                assert isinstance(s, (str, unicode))
            return s

    #
    # CoffeeScriptTraverser contexts...
    #

    # ClassDef(identifier name, expr* bases, stmt* body, expr* decorator_list)

    def do_ClassDef(self, node):

        result = self.leading_lines(node)
        tail = self.trailing_comment(node)
        name = node.name # Only a plain string is valid.
        bases = [self.visit(z) for z in node.bases] if node.bases else []
        if bases:
            s = 'class %s extends %s' % (name, ', '.join(bases))
        else:
            s = 'class %s' % name
        result.append(self.indent(s + tail))
        self.class_stack.append(name)
        for i, z in enumerate(node.body):
            self.level += 1
            result.append(self.visit(z))
            self.level -= 1
        self.class_stack.pop()
        return ''.join(result)

    # FunctionDef(identifier name, arguments args, stmt* body, expr* decorator_list)

    def do_FunctionDef(self, node):
        '''Format a FunctionDef node.'''
        result = self.leading_lines(node)
        if node.decorator_list:
            for z in node.decorator_list:
                tail = self.trailing_comment(z)
                s = '@%s' % self.visit(z)
                result.append(self.indent(s + tail))
        name = node.name # Only a plain string is valid.
        args = self.visit(node.args) if node.args else ''
        args = [z.strip() for z in args.split(',')]
        if self.class_stack and args and args[0] == '@':
            args = args[1:]
        args = ', '.join(args)
        args = '(%s) ' % args if args else ''
        # result.append('\n')
        tail = self.trailing_comment(node)
        sep = ': ' if self.class_stack else ' = '
        s = '%s%s%s->%s' % (name, sep, args, tail)
        result.append(self.indent(s))
        for i, z in enumerate(node.body):
            self.level += 1
            result.append(self.visit(z))
            self.level -= 1
        return ''.join(result)

    def do_Interactive(self, node):
        for z in node.body:
            self.visit(z)

    def do_Module(self, node):

        return ''.join([self.visit(z) for z in node.body])

    def do_Lambda(self, node):
        return self.indent('lambda %s: %s' % (
            self.visit(node.args),
            self.visit(node.body)))

    #
    # CoffeeScriptTraverser expressions...
    #

    def do_Expr(self, node):
        '''An outer expression: must be indented.'''
        head = self.leading_string(node)
        tail = self.trailing_comment(node)
        s = '%s' % self.visit(node.value)
        return head + self.indent(s) + tail

    def do_Expression(self, node):
        '''An inner expression: do not indent.'''
        return '%s\n' % self.visit(node.body)

    def do_GeneratorExp(self, node):
        elt = self.visit(node.elt) or ''
        gens = [self.visit(z) for z in node.generators]
        gens = [z if z else '<**None**>' for z in gens] # Kludge: probable bug.
        return '<gen %s for %s>' % (elt, ','.join(gens))

    #
    # CoffeeScriptTraverser operands...
    #

    # arguments = (expr* args, identifier? vararg, identifier? kwarg, expr* defaults)

    def do_arguments(self, node):
        '''Format the arguments node.'''
        assert isinstance(node, ast.arguments)
        args = [self.visit(z) for z in node.args]
        defaults = [self.visit(z) for z in node.defaults]
        # Assign default values to the last args.
        args2 = []
        n_plain = len(args) - len(defaults)
        for i in range(len(args)):
            if i < n_plain:
                args2.append(args[i])
            else:
                args2.append('%s=%s' % (args[i], defaults[i - n_plain]))
        # Now add the vararg and kwarg args.
        name = getattr(node, 'vararg', None)
        if name:
            # pylint: disable=no-member
            if isPython3 and isinstance(name, ast.arg):
                name = name.arg
            args2.append('*' + name)
        name = getattr(node, 'kwarg', None)
        if name:
            # pylint: disable=no-member
            if isPython3 and isinstance(name, ast.arg):
                name = name.arg
            args2.append('**' + name)
        return ','.join(args2)

    # Python 3:
    # arg = (identifier arg, expr? annotation)

    def do_arg(self, node):
        return node.arg

    # Attribute(expr value, identifier attr, expr_context ctx)

    def do_Attribute(self, node):
        
        # Don't visit node.attr: it is always a string.
        val = self.visit(node.value)
        val = '@' if val == '@' else val + '.'
        return val + node.attr

    def do_Bytes(self, node): # Python 3.x only.
        return str(node.s)

    # Call(expr func, expr* args, keyword* keywords, expr? starargs, expr? kwargs)

    def do_Call(self, node):
        func = self.visit(node.func)
        args = [self.visit(z) for z in node.args]
        for z in node.keywords:
            # Calls f.do_keyword.
            args.append(self.visit(z))
        if getattr(node, 'starargs', None):
            args.append('*%s' % (self.visit(node.starargs)))
        if getattr(node, 'kwargs', None):
            args.append('**%s' % (self.visit(node.kwargs)))
        args = [z for z in args if z] # Kludge: Defensive coding.
        s = '%s(%s)' % (func, ','.join(args))
        return s

    # keyword = (identifier arg, expr value)

    def do_keyword(self, node):
        # node.arg is a string.
        value = self.visit(node.value)
        # This is a keyword *arg*, not a Python keyword!
        return '%s=%s' % (node.arg, value)

    def do_comprehension(self, node):
        result = []
        name = self.visit(node.target) # A name.
        it = self.visit(node.iter) # An attribute.
        result.append('%s in %s' % (name, it))
        ifs = [self.visit(z) for z in node.ifs]
        if ifs:
            result.append(' if %s' % (''.join(ifs)))
        return ''.join(result)

    def do_Dict(self, node):
        assert len(node.keys) == len(node.values)
        items, result = [], []
        result.append('{')
        self.level += 1
        for i, key in enumerate(node.keys):
            head = self.leading_lines(key)
                # Prevents leading lines from being handled again.
            head = [z for z in head if z.strip()]
                # Ignore blank lines.
            if head:
                items.extend('\n'+''.join(head))
            tail = self.trailing_comment(node.values[i])
            key = self.visit(node.keys[i])
            value = self.visit(node.values[i])
            s = '%s:%s%s' % (key, value, tail)
            items.append(self.indent(s))
        self.level -= 1
        result.extend(items)
        if items:
            result.append(self.indent('}'))
        else:
            result.append('}')
        return ''.join(result)

    def do_Ellipsis(self, node):
        return '...'

    def do_ExtSlice(self, node):
        return ':'.join([self.visit(z) for z in node.dims])

    def do_Index(self, node):
        return self.visit(node.value)

    def do_List(self, node):
        # Not used: list context.
        # self.visit(node.ctx)
        elts = [self.visit(z) for z in node.elts]
        elst = [z for z in elts if z] # Defensive.
        return '[%s]' % ','.join(elts)

    def do_ListComp(self, node):
        elt = self.visit(node.elt)
        gens = [self.visit(z) for z in node.generators]
        gens = [z if z else '<**None**>' for z in gens] # Kludge: probable bug.
        return '%s for %s' % (elt, ''.join(gens))

    def do_Name(self, node):
        return '@' if node.id == 'self' else node.id

    def do_NameConstant(self, node): # Python 3 only.
        s = repr(node.value)
        return 'bool' if s in ('True', 'False') else s

    def do_Num(self, node):
        return repr(node.n)

    # Python 2.x only

    def do_Repr(self, node):
        return 'repr(%s)' % self.visit(node.value)

    def do_Slice(self, node):
        lower, upper, step = '', '', ''
        if getattr(node, 'lower', None) is not None:
            lower = self.visit(node.lower)
        if getattr(node, 'upper', None) is not None:
            upper = self.visit(node.upper)
        if getattr(node, 'step', None) is not None:
            step = self.visit(node.step)
        if step:
            return '%s:%s:%s' % (lower, upper, step)
        else:
            return '%s:%s' % (lower, upper)

    def do_Str(self, node):
        '''A string constant, including docstrings.'''
        if hasattr(node, 'lineno'):
            # Do *not* handle leading lines here.
            # leading = self.leading_string(node)
            return self.sync_string(node)
        else:
            g.trace('==== no lineno', node.s)
            return node.s

    # Subscript(expr value, slice slice, expr_context ctx)

    def do_Subscript(self, node):
        value = self.visit(node.value)
        the_slice = self.visit(node.slice)
        return '%s[%s]' % (value, the_slice)

    def do_Tuple(self, node):
        elts = [self.visit(z) for z in node.elts]
        return '(%s)' % ', '.join(elts)

    #
    # CoffeeScriptTraverser operators...
    #

    def op_name (self,node,strict=True):
        '''Return the print name of an operator node.'''
        d = {
            # Binary operators. 
            'Add':       '+',
            'BitAnd':    '&',
            'BitOr':     '|',
            'BitXor':    '^',
            'Div':       '/',
            'FloorDiv':  '//',
            'LShift':    '<<',
            'Mod':       '%',
            'Mult':      '*',
            'Pow':       '**',
            'RShift':    '>>',
            'Sub':       '-',
            # Boolean operators.
            'And':   ' and ',
            'Or':    ' or ',
            # Comparison operators
            'Eq':    '==',
            'Gt':    '>',
            'GtE':   '>=',
            'In':    ' in ',
            'Is':    ' is ',
            'IsNot': ' is not ',
            'Lt':    '<',
            'LtE':   '<=',
            'NotEq': '!=',
            'NotIn': ' not in ',
            # Context operators.
            'AugLoad':  '<AugLoad>',
            'AugStore': '<AugStore>',
            'Del':      '<Del>',
            'Load':     '<Load>',
            'Param':    '<Param>',
            'Store':    '<Store>',
            # Unary operators.
            'Invert':   '~',
            'Not':      ' not ',
            'UAdd':     '+',
            'USub':     '-',
        }
        kind = node.__class__.__name__
        name = d.get(kind,'<%s>' % kind)
        if strict: assert name, kind
        return name

    def do_BinOp(self, node):
        return '%s%s%s' % (
            self.visit(node.left),
            self.op_name(node.op),
            self.visit(node.right))

    def do_BoolOp(self, node):
        op_name = self.op_name(node.op)
        values = [self.visit(z) for z in node.values]
        return op_name.join(values)

    def do_Compare(self, node):
        result = []
        lt = self.visit(node.left)
        ops = [self.op_name(z) for z in node.ops]
        comps = [self.visit(z) for z in node.comparators]
        result.append(lt)
        if len(ops) == len(comps):
            for i in range(len(ops)):
                result.append('%s%s' % (ops[i], comps[i]))
        else:
            print('can not happen: ops', repr(ops), 'comparators', repr(comps))
        return ''.join(result)

    def do_IfExp(self, node):
        return '%s if %s else %s ' % (
            self.visit(node.body),
            self.visit(node.test),
            self.visit(node.orelse))

    def do_UnaryOp(self, node):
        return '%s%s' % (
            self.op_name(node.op),
            self.visit(node.operand))

    #
    # CoffeeScriptTraverser statements...
    #

    def do_Assert(self, node):
        
        head = self.leading_string(node)
        tail = self.trailing_comment(node)
        test = self.visit(node.test)
        if getattr(node, 'msg', None) is not None:
            s = 'assert %s, %s' % (test, self.visit(node.msg))
        else:
            s = 'assert %s' % test
        return head + self.indent(s) + tail

    def do_Assign(self, node):

        head = self.leading_string(node)
        tail = self.trailing_comment(node)
        s = '%s=%s' % (
            '='.join([self.visit(z) for z in node.targets]),
            self.visit(node.value))
        return head + self.indent(s) + tail

    def do_AugAssign(self, node):
        
        head = self.leading_string(node)
        tail = self.trailing_comment(node)
        s = '%s%s=%s' % (
            self.visit(node.target),
            self.op_name(node.op),
            self.visit(node.value))
        return head + self.indent(s) + tail

    def do_Break(self, node):
        
        head = self.leading_string(node)
        tail = self.trailing_comment(node)
        return head + self.indent('break') + tail

    def do_Continue(self, node):
        
        head = self.leading_lines(node)
        tail = self.trailing_comment(node)
        return head + self.indent('continue') + tail

    def do_Delete(self, node):
        
        head = self.leading_string(node)
        tail = self.trailing_comment(node)
        targets = [self.visit(z) for z in node.targets]
        s = 'del %s' % ','.join(targets)
        return head + self.indent(s) + tail

    def do_ExceptHandler(self, node):

        result = self.leading_lines(node)
        tail = self.trailing_comment(node)
        result.append(self.indent('except'))
        if getattr(node, 'type', None):
            result.append(' %s' % self.visit(node.type))
        if getattr(node, 'name', None):
            if isinstance(node.name, ast.AST):
                result.append(' as %s' % self.visit(node.name))
            else:
                result.append(' as %s' % node.name) # Python 3.x.
        result.append(':' + tail)
        for z in node.body:
            self.level += 1
            result.append(self.visit(z))
            self.level -= 1
        return ''.join(result)

    # Python 2.x only

    def do_Exec(self, node):
        
        head = self.leading_string(node)
        tail = self.trailing_comment(node)
        body = self.visit(node.body)
        args = [] # Globals before locals.
        if getattr(node, 'globals', None):
            args.append(self.visit(node.globals))
        if getattr(node, 'locals', None):
            args.append(self.visit(node.locals))
        if args:
            s = 'exec %s in %s' % (body, ','.join(args))
        else:
            s = 'exec %s' % body
        return head + self.indent(s) + tail

    def do_For(self, node):

        result = self.leading_lines(node)
        tail = self.trailing_comment(node)
        s = 'for %s in %s:' % (
            self.visit(node.target),
            self.visit(node.iter))
        result.append(self.indent(s + tail))
        for z in node.body:
            self.level += 1
            result.append(self.visit(z))
            self.level -= 1
        if node.orelse:
            # TODO: how to get a comment following the else?
            result.append(self.indent('else:\n'))
            for z in node.orelse:
                self.level += 1
                result.append(self.visit(z))
                self.level -= 1
        return ''.join(result)

    def do_Global(self, node):
        
        head = self.leading_lines(node)
        tail = self.trailing_comment(node)
        s = 'global %s' % ','.join(node.names)
        return head + self.indent(s) + tail

    def do_If(self, node):

        result = self.leading_lines(node)
        tail = self.trailing_comment(node)
        s = 'if %s:%s' % (self.visit(node.test), tail)
        result.append(self.indent(s))
        for z in node.body:
            self.level += 1
            result.append(self.visit(z))
            self.level -= 1
        if node.orelse:
            # TODO: how to get a comment following the else?
            result.append(self.indent('else:\n'))
            for z in node.orelse:
                self.level += 1
                result.append(self.visit(z))
                self.level -= 1
        return ''.join(result)

    def do_Import(self, node):
        
        head = self.leading_string(node)
        tail = self.trailing_comment(node)
        names = []
        for fn, asname in self.get_import_names(node):
            if asname:
                names.append('%s as %s' % (fn, asname))
            else:
                names.append(fn)
        s = 'pass # import %s' % ','.join(names)
        return head + self.indent(s) + tail

    def get_import_names(self, node):
        '''Return a list of the the full file names in the import statement.'''
        result = []
        for ast2 in node.names:
            assert isinstance(ast2, ast.alias)
            data = ast2.name, ast2.asname
            result.append(data)
        return result

    def do_ImportFrom(self, node):

        head = self.leading_string(node)
        tail = self.trailing_comment(node)
        names = []
        for fn, asname in self.get_import_names(node):
            if asname:
                names.append('%s as %s' % (fn, asname))
            else:
                names.append(fn)
        s = 'pass # from %s import %s' % (node.module, ','.join(names))
        return head + self.indent(s) + tail

    def do_Pass(self, node):
        
        head = self.leading_string(node)
        tail = self.trailing_comment(node)
        return head + self.indent('pass') + tail

    # Python 2.x only

    def do_Print(self, node):
        
        head = self.leading_string(node)
        tail = self.trailing_comment(node)
        vals = []
        for z in node.values:
            vals.append(self.visit(z))
        if getattr(node, 'dest', None) is not None:
            vals.append('dest=%s' % self.visit(node.dest))
        if getattr(node, 'nl', None) is not None:
            if node.nl == 'False':
                vals.append('nl=%s' % node.nl)
        s = 'print(%s)' % ','.join(vals)
        return head + self.indent(s) + tail

    def do_Raise(self, node):
        
        head = self.leading_string(node)
        tail = self.trailing_comment(node)
        args = []
        for attr in ('type', 'inst', 'tback'):
            if getattr(node, attr, None) is not None:
                args.append(self.visit(getattr(node, attr)))
        s = 'raise %s' % ', '.join(args) if args else 'raise'
        return head + self.indent(s) + tail

    def do_Return(self, node):
        
        head = self.leading_string(node)
        tail = self.trailing_comment(node)
        if node.value:
            s = 'return %s' % self.visit(node.value).strip()
        else:
            s = 'return'
        return head + self.indent(s) + tail

    # Try(stmt* body, excepthandler* handlers, stmt* orelse, stmt* finalbody)

    def do_Try(self, node): # Python 3

        result = self.leading_lines(node)
        tail = self.trailing_comment(node)
        s = 'try' + tail
        result.append(self.indent(s))
        for z in node.body:
            self.level += 1
            result.append(self.visit(z))
            self.level -= 1
        if node.handlers:
            for z in node.handlers:
                result.append(self.visit(z))
        if node.orelse:
            tail = self.trailing_comment(node.orelse)
            result.append(self.indent('else:' + tail))
            for z in node.orelse:
                self.level += 1
                result.append(self.visit(z))
                self.level -= 1
        if node.finalbody:
            tail = self.trailing_comment(node.finalbody)
            s = 'finally:' + tail
            result.append(self.indent(s))
            for z in node.finalbody:
                self.level += 1
                result.append(self.visit(z))
                self.level -= 1
        return ''.join(result)

    def do_TryExcept(self, node):

        result = self.leading_lines(node)
        tail = self.trailing_comment(node)
        s = 'try:' + tail
        result.append(self.indent(s))
        for z in node.body:
            self.level += 1
            result.append(self.visit(z))
            self.level -= 1
        if node.handlers:
            for z in node.handlers:
                result.append(self.visit(z))
        if node.orelse:
            tail = self.trailing_comment(node.orelse)
            s = 'else:' + tail
            result.append(self.indent(s))
            for z in node.orelse:
                self.level += 1
                result.append(self.visit(z))
                self.level -= 1
        return ''.join(result)

    def do_TryFinally(self, node):
        
        result = self.leading_lines(node)
        tail = self.trailing_comment(node)
        result.append(self.indent('try:' + tail))
        for z in node.body:
            self.level += 1
            result.append(self.visit(z))
            self.level -= 1
        # TODO: how to attach comments that appear after 'finally'?
        result.append(self.indent('finally:\n'))
        for z in node.finalbody:
            self.level += 1
            result.append(self.visit(z))
            self.level -= 1
        return ''.join(result)

    def do_While(self, node):
        
        result = self.leading_lines(node)
        tail = self.trailing_comment(node)
        s = 'while %s:' % self.visit(node.test)
        result.append(self.indent(s + tail))
        for z in node.body:
            self.level += 1
            result.append(self.visit(z))
            self.level -= 1
        if node.orelse:
            tail = self.trailing_comment(node)
            result.append(self.indent('else:' + tail))
            for z in node.orelse:
                self.level += 1
                result.append(self.visit(z))
                self.level -= 1
        return ''.join(result)

    def do_With(self, node):

        result = self.leading_lines(node)
        tail = self.trailing_comment(node)
        result.append(self.indent('with '))
        if hasattr(node, 'context_expression'):
            result.append(self.visit(node.context_expresssion))
        vars_list = []
        if hasattr(node, 'optional_vars'):
            try:
                for z in node.optional_vars:
                    vars_list.append(self.visit(z))
            except TypeError: # Not iterable.
                vars_list.append(self.visit(node.optional_vars))
        result.append(','.join(vars_list))
        result.append(':' + tail)
        for z in node.body:
            self.level += 1
            result.append(self.visit(z))
            self.level -= 1
        result.append('\n')
        return ''.join(result)

    def do_Yield(self, node):
        
        head = self.leading_string(node)
        tail = self.trailing_comment(node)
        if getattr(node, 'value', None) is not None:
            s = 'yield %s' % self.visit(node.value)
        else:
            s ='yield'
        return head + self.indent(s) + tail


class LeoGlobals(object):
    '''A class supporting g.pdb and g.trace for compatibility with Leo.'''


    class NullObject:
        """
        An object that does nothing, and does it very well.
        From the Python cookbook, recipe 5.23
        """
        def __init__(self, *args, **keys): pass
        def __call__(self, *args, **keys): return self
        def __repr__(self): return "NullObject"
        def __str__(self): return "NullObject"
        def __bool__(self): return False
        def __nonzero__(self): return 0
        def __delattr__(self, attr): return self
        def __getattr__(self, attr): return self
        def __setattr__(self, attr, val): return self


    class ReadLinesClass:
        """A class whose next method provides a readline method for Python's tokenize module."""

        def __init__(self, s):
            self.lines = s.splitlines(True) if s else []
                # g.splitLines(s)
            self.i = 0

        def next(self):
            if self.i < len(self.lines):
                line = self.lines[self.i]
                self.i += 1
            else:
                line = ''
            # g.trace(repr(line))
            return line

        __next__ = next

    def _callerName(self, n=1, files=False):
        # print('_callerName: %s %s' % (n,files))
        try: # get the function name from the call stack.
            f1 = sys._getframe(n) # The stack frame, n levels up.
            code1 = f1.f_code # The code object
            name = code1.co_name
            if name == '__init__':
                name = '__init__(%s,line %s)' % (
                    self.shortFileName(code1.co_filename), code1.co_firstlineno)
            if files:
                return '%s:%s' % (self.shortFileName(code1.co_filename), name)
            else:
                return name # The code name
        except ValueError:
            # print('g._callerName: ValueError',n)
            return '' # The stack is not deep enough.
        except Exception:
            # es_exception()
            return '' # "<no caller name>"

    def callers(self, n=4, count=0, excludeCaller=True, files=False):
        '''Return a list containing the callers of the function that called g.callerList.

        If the excludeCaller keyword is True (the default), g.callers is not on the list.

        If the files keyword argument is True, filenames are included in the list.
        '''
        # sys._getframe throws ValueError in both cpython and jython if there are less than i entries.
        # The jython stack often has less than 8 entries,
        # so we must be careful to call g._callerName with smaller values of i first.
        result = []
        i = 3 if excludeCaller else 2
        while 1:
            s = self._callerName(i, files=files)
            # print(i,s)
            if s:
                result.append(s)
            if not s or len(result) >= n: break
            i += 1
        result.reverse()
        if count > 0: result = result[: count]
        sep = '\n' if files else ','
        return sep.join(result)

    def cls(self):
        '''Clear the screen.'''
        if sys.platform.lower().startswith('win'):
            os.system('cls')

    def computeLeadingWhitespace(self, width, tab_width):
        '''Returns optimized whitespace corresponding to width with the indicated tab_width.'''
        if width <= 0:
            return ""
        elif tab_width > 1:
            tabs = int(width / tab_width)
            blanks = int(width % tab_width)
            return ('\t' * tabs) + (' ' * blanks)
        else: # Negative tab width always gets converted to blanks.
            return (' ' * width)

    def computeLeadingWhitespaceWidth(self, s, tab_width):
        '''Returns optimized whitespace corresponding to width with the indicated tab_width.'''
        w = 0
        for ch in s:
            if ch == ' ':
                w += 1
            elif ch == '\t':
                w += (abs(tab_width) - (w % abs(tab_width)))
            else:
                break
        return w

    def isString(self, s):
        '''Return True if s is any string, but not bytes.'''
        if isPython3:
            return type(s) == type('a')
        else:
            return type(s) in types.StringTypes

    def isUnicode(self, s):
        '''Return True if s is a unicode string.'''
        if isPython3:
            return type(s) == type('a')
        else:
            return type(s) == types.UnicodeType

    def pdb(self):
        try:
            import leo.core.leoGlobals as leo_g
            leo_g.pdb()
        except ImportError:
            import pdb
            pdb.set_trace()

    def shortFileName(self, fileName, n=None):
        if n is None or n < 1:
            return os.path.basename(fileName)
        else:
            return '/'.join(fileName.replace('\\', '/').split('/')[-n:])

    def splitLines(self, s):
        '''Split s into lines, preserving trailing newlines.'''
        return s.splitlines(True) if s else []

    def toUnicode(self, s, encoding='utf-8', reportErrors=False):
        '''Connvert a non-unicode string with the given encoding to unicode.'''
        trace = False
        if g.isUnicode(s):
            return s
        if not encoding:
            encoding = 'utf-8'
        # These are the only significant calls to s.decode in Leo.
        # Tracing these calls directly yields thousands of calls.
        # Never call g.trace here!
        try:
            s = s.decode(encoding, 'strict')
        except UnicodeError:
            s = s.decode(encoding, 'replace')
            if trace or reportErrors:
                g.trace(g.callers())
                print("toUnicode: Error converting %s... from %s encoding to unicode" % (
                    s[: 200], encoding))
        except AttributeError:
            if trace:
                print('toUnicode: AttributeError!: %s' % s)
            # May be a QString.
            s = g.u(s)
        if trace and encoding == 'cp1252':
            print('toUnicode: returns %s' % s)
        return s

    def trace(self, *args, **keys):
        try:
            import leo.core.leoGlobals as leo_g
            leo_g.trace(caller_level=2, *args, **keys)
        except ImportError:
            print(args, keys)

    if isPython3:

        def u(self, s):
            return s

        def ue(self, s, encoding):
            return s if g.isUnicode(s) else str(s, encoding)

    else:

        def u(self, s):
            return unicode(s)

        def ue(self, s, encoding):
            return unicode(s, encoding)


class MakeCoffeeScriptController(object):
    '''The controller class for python_to_coffeescript.py.'''


    def __init__(self):
        '''Ctor for MakeCoffeeScriptController class.'''
        self.options = {}
        # Ivars set on the command line...
        self.config_fn = None
        self.enable_unit_tests = False
        self.files = [] # May also be set in the config file.
        self.section_names = ('Global',)
        # Ivars set in the config file...
        self.output_directory = self.finalize('.')
        self.overwrite = False
        self.verbose = False # Trace config arguments.

    def finalize(self, fn):
        '''Finalize and regularize a filename.'''
        fn = os.path.expanduser(fn)
        fn = os.path.abspath(fn)
        fn = os.path.normpath(fn)
        return fn

    def make_coffeescript_file(self, fn):
        '''
        Make a stub file in the output directory for all source files mentioned
        in the [Source Files] section of the configuration file.
        '''
        if not fn.endswith('.py'):
            print('not a python file', fn)
            return
        if not os.path.exists(fn):
            print('not found', fn)
            return
        base_fn = os.path.basename(fn)
        out_fn = os.path.join(self.output_directory, base_fn)
        out_fn = os.path.normpath(out_fn)
        out_fn = out_fn[: -3] + '.coffee'
        dir_ = os.path.dirname(out_fn)
        if os.path.exists(out_fn) and not self.overwrite:
            print('file exists: %s' % out_fn)
        elif not dir_ or os.path.exists(dir_):
            t1 = time.clock()
            s = open(fn).read()
            readlines = g.ReadLinesClass(s).next
            tokens = list(tokenize.generate_tokens(readlines))
            # s = CoffeeScriptTokenizer(controller=self).format(tokens)
            node = ast.parse(s, filename=fn, mode='exec')
            s = CoffeeScriptTraverser(controller=self).format(node, s, tokens)
            f = open(out_fn, 'w')
            self.output_time_stamp(f)
            f.write(s)
            f.close()
            print('wrote: %s' % out_fn)
        else:
            print('output directory not not found: %s' % dir_)

    def output_time_stamp(self, f):
        '''Put a time-stamp in the output file f.'''
        f.write('# python_to_coffeescript: %s\n' %
            time.strftime("%a %d %b %Y at %H:%M:%S"))

    def run(self):
        '''
        Make stub files for all files.
        Do nothing if the output directory does not exist.
        '''
        if self.enable_unit_tests:
            self.run_all_unit_tests()
        if self.files:
            dir_ = self.output_directory
            if dir_:
                if os.path.exists(dir_):
                    for fn in self.files:
                        self.make_coffeescript_file(fn)
                else:
                    print('output directory not found: %s' % dir_)
            else:
                print('no output directory')
        elif not self.enable_unit_tests:
            print('no input files')

    def run_all_unit_tests(self):
        '''Run all unit tests in the python-to-coffeescript/test directory.'''
        import unittest
        loader = unittest.TestLoader()
        suite = loader.discover(os.path.abspath('.'),
                                pattern='test*.py',
                                top_level_dir=None)
        unittest.TextTestRunner(verbosity=1).run(suite)

    def scan_command_line(self):
        '''Set ivars from command-line arguments.'''
        # This automatically implements the --help option.
        usage = "usage: python_to_coffeescript.py [options] file1, file2, ..."
        parser = optparse.OptionParser(usage=usage)
        add = parser.add_option
        add('-c', '--config', dest='fn',
            help='full path to configuration file')
        add('-d', '--dir', dest='dir',
            help='full path to the output directory')
        add('-o', '--overwrite', action='store_true', default=False,
            help='overwrite existing .coffee files')
        # add('-t', '--test', action='store_true', default=False,
            # help='run unit tests on startup')
        add('-v', '--verbose', action='store_true', default=False,
            help='verbose output')
        # Parse the options
        options, args = parser.parse_args()
        # Handle the options...
        # self.enable_unit_tests = options.test
        self.overwrite = options.overwrite
        if options.fn:
            self.config_fn = options.fn
        if options.dir:
            dir_ = options.dir
            dir_ = self.finalize(dir_)
            if os.path.exists(dir_):
                self.output_directory = dir_
            else:
                print('--dir: directory does not exist: %s' % dir_)
                print('exiting')
                sys.exit(1)
        # If any files remain, set self.files.
        if args:
            args = [self.finalize(z) for z in args]
            if args:
                self.files = args

    def scan_options(self):
        '''Set all configuration-related ivars.'''
        trace = False
        if not self.config_fn:
            return
        self.parser = parser = self.create_parser()
        s = self.get_config_string()
        self.init_parser(s)
        if self.files:
            files_source = 'command-line'
            files = self.files
        elif parser.has_section('Global'):
            files_source = 'config file'
            files = parser.get('Global', 'files')
            files = [z.strip() for z in files.split('\n') if z.strip()]
        else:
            return
        files2 = []
        for z in files:
            files2.extend(glob.glob(self.finalize(z)))
        self.files = [z for z in files2 if z and os.path.exists(z)]
        if trace:
            print('Files (from %s)...\n' % files_source)
            for z in self.files:
                print(z)
            print('')
        if 'output_directory' in parser.options('Global'):
            s = parser.get('Global', 'output_directory')
            output_dir = self.finalize(s)
            if os.path.exists(output_dir):
                self.output_directory = output_dir
                if self.verbose:
                    print('output directory: %s\n' % output_dir)
            else:
                print('output directory not found: %s\n' % output_dir)
                self.output_directory = None # inhibit run().
        if 'prefix_lines' in parser.options('Global'):
            prefix = parser.get('Global', 'prefix_lines')
            self.prefix_lines = prefix.split('\n')
                # The parser does not preserve leading whitespace.
            if trace:
                print('Prefix lines...\n')
                for z in self.prefix_lines:
                    print(z)
                print('')
        #
        # self.def_patterns = self.scan_patterns('Def Name Patterns')
        # self.general_patterns = self.scan_patterns('General Patterns')
        # self.make_patterns_dict()

    def create_parser(self):
        '''Create a RawConfigParser and return it.'''
        parser = configparser.RawConfigParser()
        parser.optionxform = str
        return parser

    def get_config_string(self):
        fn = self.finalize(self.config_fn)
        if os.path.exists(fn):
            if self.verbose:
                print('\nconfiguration file: %s\n' % fn)
            f = open(fn, 'r')
            s = f.read()
            f.close()
            return s
        else:
            print('\nconfiguration file not found: %s' % fn)
            return ''

    def init_parser(self, s):
        '''Add double back-slashes to all patterns starting with '['.'''
        trace = False
        if not s: return
        aList = []
        for s in s.split('\n'):
            if self.is_section_name(s):
                aList.append(s)
            elif s.strip().startswith('['):
                aList.append(r'\\' + s[1:])
                if trace: g.trace('*** escaping:', s)
            else:
                aList.append(s)
        s = '\n'.join(aList) + '\n'
        if trace: g.trace(s)
        file_object = io.StringIO(s)
        self.parser.readfp(file_object)

    def is_section_name(self, s):

        def munge(s):
            return s.strip().lower().replace(' ', '')

        s = s.strip()
        if s.startswith('[') and s.endswith(']'):
            s = munge(s[1: -1])
            for s2 in self.section_names:
                if s == munge(s2):
                    return True
        return False


class ParseState(object):
    '''A class representing items parse state stack.'''

    def __init__(self, kind, value):
        self.kind = kind
        self.value = value

    def __repr__(self):
        return 'State: %10s %s' % (self.kind, repr(self.value))

    __str__ = __repr__


class TokenSync(object):
    '''A class to sync and remember tokens.'''
    # To do: handle comments, line breaks...

    def __init__(self, s, tokens):
        '''Ctor for TokenSync class.'''
        assert isinstance(tokens, list) # Not a generator.
        self.s = s
        self.first_leading_line = None
        self.lines = [z.rstrip() for z in g.splitLines(s)]
        # Order is important from here on...
        self.nl_token = self.make_nl_token()
        self.line_tokens = self.make_line_tokens(tokens)
        self.blank_lines = self.make_blank_lines()
        self.string_tokens = self.make_string_tokens()
        self.ignored_lines = self.make_ignored_lines()

    def make_blank_lines(self):
        '''Return of list of line numbers of blank lines.'''
        result = []
        for i, aList in enumerate(self.line_tokens):
            # if any([self.token_kind(z) == 'nl' for z in aList]):
            if len(aList) == 1 and self.token_kind(aList[0]) == 'nl':
                result.append(i)
        return result

    def make_ignored_lines(self):
        '''
        Return a copy of line_tokens containing ignored lines,
        that is, full-line comments or blank lines.
        These are the lines returned by leading_lines().
        '''
        result = []
        for i, aList in enumerate(self.line_tokens):
            for z in aList:
                if self.is_line_comment(z):
                    result.append(z)
                    break
            else:
                if i in self.blank_lines:
                    result.append(self.nl_token)
                else:
                    result.append(None)
        assert len(result) == len(self.line_tokens)
        for i, aList in enumerate(result):
            if aList:
                self.first_leading_line = i
                break
        else:
            self.first_leading_line = len(result)
        return result

    def make_line_tokens(self, tokens):
        '''
        Return a list of lists of tokens for each list in self.lines.
        The strings in self.lines may end in a backslash, so care is needed.
        '''
        trace = False
        n, result = len(self.lines), []
        for i in range(0, n+1):
            result.append([])
        for token in tokens:
            t1, t2, t3, t4, t5 = token
            kind = token_module.tok_name[t1].lower()
            srow, scol = t3
            erow, ecol = t4
            line = erow-1 if kind == 'string' else srow-1 
            result[line].append(token)
            if trace: g.trace('%3s %s' % (line, self.dump_token(token)))
        assert len(self.lines) + 1 == len(result), len(result)
        return result

    def make_nl_token(self):
        '''Return a newline token with '\n' as both val and raw_val.'''
        t1 = token_module.NEWLINE
        t2 = '\n'
        t3 = (0, 0) # Not used.
        t4 = (0, 0) # Not used.
        t5 = '\n'
        return t1, t2, t3, t4, t5

    def make_string_tokens(self):
        '''Return a copy of line_tokens containing only string tokens.'''
        result = []
        for aList in self.line_tokens:
            result.append([z for z in aList if self.token_kind(z) == 'string'])
        assert len(result) == len(self.line_tokens)
        return result

    def dump_token(self, token):
        '''Dump the token for debugging.'''
        t1, t2, t3, t4, t5 = token
        kind = g.toUnicode(token_module.tok_name[t1].lower())
        raw_val = g.toUnicode(t5)
        val = g.toUnicode(t2)
        return 'token: %10s %r' % (kind, val)

    def is_line_comment(self, token):
        '''Return True if the token represents a full-line comment.'''
        t1, t2, t3, t4, t5 = token
        kind = token_module.tok_name[t1].lower()
        raw_val = t5
        return kind == 'comment' and raw_val.lstrip().startswith('#')

    def leading_lines(self, node):
        '''Return a list of the preceding comment and blank lines'''
        # This can be called on arbitrary nodes.
        trace = False
        leading = []
        if hasattr(node, 'lineno'):
            i, n = self.first_leading_line, node.lineno
            while i < n:
                token = self.ignored_lines[i]
                if token:
                    s = self.token_raw_val(token).rstrip()+'\n'
                    leading.append(s)
                    if trace: g.trace('%11s: %s' % (i, s.rstrip()))
                i += 1
            self.first_leading_line = i
        return leading

    def leading_string(self, node):
        '''Return a string containing all lines preceding node.'''
        return ''.join(self.leading_lines(node))

    def line_at(self, node, continued_lines=True):
        '''Return the lines at the node, possibly including continuation lines.'''
        n = getattr(node, 'lineno', None)
        if n is None:
            return '<no line> for %s' % node.__class__.__name__
        elif continued_lines:
            aList, n = [], n-1
            while n < len(self.lines):
                s = self.lines[n]
                if s.endswith('\\'):
                    aList.append(s[:-1])
                    n += 1
                else:
                    aList.append(s)
                    break
            return ''.join(aList)
        else:
            return self.lines[n-1]

    def sync_string(self, node):
        '''Return the spelling of the string at the given node.'''
        # g.trace('%-10s %2s: %s' % (' ', node.lineno, self.line_at(node)))
        n = node.lineno
        tokens = self.string_tokens[n-1]
        if tokens:
            token = tokens.pop(0)
            self.string_tokens[n-1] = tokens
            return self.token_val(token)
        else:
            g.trace('===== underflow', n, node.s)
            return node.s

    def token_kind(self, token):
        '''Return the token's type.'''
        t1, t2, t3, t4, t5 = token
        return g.toUnicode(token_module.tok_name[t1].lower())

    def token_raw_val(self, token):
        '''Return the value of the token.'''
        t1, t2, t3, t4, t5 = token
        return g.toUnicode(t5)
        
    def token_val(self, token):
        '''Return the raw value of the token.'''
        t1, t2, t3, t4, t5 = token
        return g.toUnicode(t2)

    def trailing_comment(self, node):
        '''
        Return a string containing the trailing comment for the node, if any.
        The string always ends with a newline.
        '''
        n = getattr(node, 'lineno', None)
        if n is not None:
            tokens = self.line_tokens[node.lineno-1]
            for token in tokens:
                if self.token_kind(token) == 'comment':
                    raw_val = self.token_raw_val(token).rstrip()
                    if not raw_val.strip().startswith('#'):
                        val = self.token_val(token).rstrip()
                        s = ' %s\n' % val
                        # g.trace(node.lineno, s.rstrip(), g.callers())
                        return s
            return '\n'
        g.trace('no lineno', node.__class__.__name__, g.callers())
        return '\n'

g = LeoGlobals() # For ekr.
if __name__ == "__main__":
    main()

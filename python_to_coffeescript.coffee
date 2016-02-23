# python_to_coffeescript: Tue 23 Feb 2016 at 02:19:09
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
pass # import ast
pass # import glob
pass # import optparse
pass # import os
pass # import sys
pass # import time
pass # import token as token_module
pass # import tokenize
pass # import types
try:
    pass # import ConfigParser as configparser
except ImportError:
    pass # import configparser
try:
    pass # import StringIO as io
except ImportError:
    pass # import io
isPython3=sys.version_info>=(3, 0, 0)

main = ->
    '''
    The driver for the stand-alone version of make-stub-files.
    All options come from ~/stubs/make_stub_files.cfg.
    '''
    # g.cls()
    controller=MakeCoffeeScriptController()
    controller.scan_command_line()
    controller.scan_options()
    controller.run()
    print('done')
#
# Utility functions...
#

dump = (title, s=None) ->
    if s:
        print('===== %s...\n%s\n'%(title, s.rstrip()))
    else:
        print('===== %s...\n'%title)

dump_dict = (title, d) ->
    '''Dump a dictionary with a header.'''
    dump(title)
    for z in sorted(d):
        print('%30s %s'%(z, d.get(z)))
    print('')

dump_list = (title, aList) ->
    '''Dump a list with a header.'''
    dump(title)
    for z in aList:
        print(z)
    print('')

pdb = (@) ->
    '''Invoke a debugger during unit testing.'''
    print('pdb')
    # Avoid try/except during development.
    # try:
        # import leo.core.leoGlobals as leo_g
        # leo_g.pdb()
    # except ImportError:
        # import pdb
        # pdb.set_trace()

truncate = (s, n) ->
    '''Return s truncated to n characters.'''
    return s if len(s)<=n else s[:n-3]+'...'


class CoffeeScriptTraverser extends object
    '''A class to convert python sources to coffeescript sources.'''
    # pylint: disable=consider-using-enumerate

    __init__: (controller) ->
        '''Ctor for CoffeeScriptFormatter class.'''
        @controller=controller
        @sync_string=None
        @leading_lines=None
        @class_stack=[]

    format: (node, s, tokens) ->
        '''Format the node (or list of nodes) and its descendants.'''
        @level=0
        sync=TokenSync(s,tokens)
        @sync_string=sync.sync_string
        @leading_lines=sync.leading_lines
        val=@visit(node)
        return val or ''

    indent: (s) ->
        '''Return s, properly indented.'''
        # assert not s.startswith('\n'), (g.callers(), repr(s))
        n=0
        while s and s.startswith('\n'):
            n+=1
            s=s[1:]
        return '%s%s%s'%('\n'*n, ' '*4*@level, s)

    visit: (node) ->
        '''Return the formatted version of an Ast node, or list of Ast nodes.'''
        name=node.__class__.__name__
        if isinstance(node,(list, tuple)):
            return ', '.join(@visit(z) for z in node)
        else:
            if node is None:
                return 'None'
            else:
                assert isinstance(node,ast.AST), name
                method=getattr(@,'do_'+name)
                s=method(node)
                if isPython3:
                    assert isinstance(s,str)
                else:
                    assert isinstance(s,(str, unicode))
                return s
    #
    # CoffeeScriptTraverser contexts...
    #
    # ClassDef(identifier name, expr* bases, stmt* body, expr* decorator_list)

    do_ClassDef: (node) ->
        result=@leading_lines(node)
        name=node.name
        bases=@visit(z) for z in node.bases if node.bases else [] 
        result.append('\n\n')
        if bases:
            # result.append(self.indent('class %s(%s):\n' % (name, ', '.join(bases))))
            result.append(@indent('class %s extends %s\n'%(name, ', '.join(bases))))
        else:
            result.append(@indent('class %s\n'%name))
        @class_stack.append(name)
        for (i, z) in enumerate(node.body):
            @level+=1
            result.append(@visit(z))
            @level-=1
        @class_stack.pop()
        return ''.join(result)
    # FunctionDef(identifier name, arguments args, stmt* body, expr* decorator_list)

    do_FunctionDef: (node) ->
        '''Format a FunctionDef node.'''
        result=@leading_lines(node)
        if node.decorator_list:
            for z in node.decorator_list:
                result.append(@indent('@%s\n'%@visit(z)))
        name=node.name
        args=@visit(node.args) if node.args else '' 
        args=z.strip() for z in args.split(',')
        if @class_stack and args and args[0]=='@':
            args=args[1:]
        args=', '.join(args)
        args='(%s) '%args if args else '' 
        result.append('\n')
        sep=': ' if @class_stack else ' = ' 
        s='%s%s%s->\n'%(name, sep, args)
        result.append(@indent(s))
        for (i, z) in enumerate(node.body):
            @level+=1
            result.append(@visit(z))
            @level-=1
        return ''.join(result)

    do_Interactive: (node) ->
        for z in node.body:
            @visit(z)

    do_Module: (node) ->
        return ''.join(@visit(z) for z in node.body)

    do_Lambda: (node) ->
        return @indent('lambda %s: %s'%(@visit(node.args), @visit(node.body)))
    #
    # CoffeeScriptTraverser expressions...
    #

    do_Expr: (node) ->
        '''An outer expression: must be indented.'''
        leading=@leading_lines(node)
        s='%s\n'%@visit(node.value)
        return ''.join(leading)+@indent(s)

    do_Expression: (node) ->
        '''An inner expression: do not indent.'''
        return '%s\n'%@visit(node.body)

    do_GeneratorExp: (node) ->
        elt=@visit(node.elt) or ''
        gens=@visit(z) for z in node.generators
        gens=z if z else '<**None**>'  for z in gens
        return '<gen %s for %s>'%(elt, ','.join(gens))

    do_AugLoad: (node) ->
        return 'AugLoad'

    do_Del: (node) ->
        return 'Del'

    do_Load: (node) ->
        return 'Load'

    do_Param: (node) ->
        return 'Param'

    do_Store: (node) ->
        return 'Store'
    #
    # CoffeeScriptTraverser operands...
    #
    # arguments = (expr* args, identifier? vararg, identifier? kwarg, expr* defaults)

    do_arguments: (node) ->
        '''Format the arguments node.'''
        assert isinstance(node,ast.arguments)
        args=@visit(z) for z in node.args
        defaults=@visit(z) for z in node.defaults
        # Assign default values to the last args.
        args2=[]
        n_plain=len(args)-len(defaults)
        for i in range(len(args)):
            if i<n_plain:
                args2.append(args[i])
            else:
                args2.append('%s=%s'%(args[i], defaults[i-n_plain]))
        # Now add the vararg and kwarg args.
        name=getattr(node,'vararg',None)
        if name:
            # pylint: disable=no-member
            if isPython3 and isinstance(name,ast.arg):
                name=name.arg
            args2.append('*'+name)
        name=getattr(node,'kwarg',None)
        if name:
            # pylint: disable=no-member
            if isPython3 and isinstance(name,ast.arg):
                name=name.arg
            args2.append('**'+name)
        return ','.join(args2)
    # Python 3:
    # arg = (identifier arg, expr? annotation)

    do_arg: (node) ->
        return node.arg
    # Attribute(expr value, identifier attr, expr_context ctx)

    do_Attribute: (node) ->
        # Don't visit node.attr: it is always a string.
        val=@visit(node.value)
        val='@' if val=='@' else val+'.' 
        return val+node.attr

    do_Bytes: (node) ->
        return str(node.s)
    # Call(expr func, expr* args, keyword* keywords, expr? starargs, expr? kwargs)

    do_Call: (node) ->
        func=@visit(node.func)
        args=@visit(z) for z in node.args
        for z in node.keywords:
            # Calls f.do_keyword.
            args.append(@visit(z))
        if getattr(node,'starargs',None):
            args.append('*%s'%@visit(node.starargs))
        if getattr(node,'kwargs',None):
            args.append('**%s'%@visit(node.kwargs))
        args=z for z in args if z
        s='%s(%s)'%(func, ','.join(args))
        return s
    # keyword = (identifier arg, expr value)

    do_keyword: (node) ->
        # node.arg is a string.
        value=@visit(node.value)
        # This is a keyword *arg*, not a Python keyword!
        return '%s=%s'%(node.arg, value)

    do_comprehension: (node) ->
        result=[]
        name=@visit(node.target)
        it=@visit(node.iter)
        result.append('%s in %s'%(name, it))
        ifs=@visit(z) for z in node.ifs
        if ifs:
            result.append(' if %s'%''.join(ifs))
        return ''.join(result)

    do_Dict: (node) ->
        result=[]
        keys=@visit(z) for z in node.keys
        values=@visit(z) for z in node.values
        if len(keys)==len(values):
            # result.append('{\n' if keys else '{')
            result.append('{')
            items=[]
            for i in range(len(keys)):
                items.append('%s:%s'%(keys[i], values[i]))
            result.append(', '.join(items))
            result.append('}')
        else:
            # result.append(',\n'.join(items))
            # result.append('\n}' if keys else '}')
            print('Error: f.Dict: len(keys) != len(values)\nkeys: %s\nvals: %s'%(repr(keys), repr(values)))
        return ''.join(result)

    do_Ellipsis: (node) ->
        return '...'

    do_ExtSlice: (node) ->
        return ':'.join(@visit(z) for z in node.dims)

    do_Index: (node) ->
        return @visit(node.value)

    do_List: (node) ->
        # Not used: list context.
        # self.visit(node.ctx)
        elts=@visit(z) for z in node.elts
        elst=z for z in elts if z
        return '[%s]'%','.join(elts)

    do_ListComp: (node) ->
        elt=@visit(node.elt)
        gens=@visit(z) for z in node.generators
        gens=z if z else '<**None**>'  for z in gens
        return '%s for %s'%(elt, ''.join(gens))

    do_Name: (node) ->
        return '@' if node.id=='self' else node.id

    do_NameConstant: (node) ->
        s=repr(node.value)
        return 'bool' if s in ('True', 'False') else s

    do_Num: (node) ->
        return repr(node.n)
    # Python 2.x only

    do_Repr: (node) ->
        return 'repr(%s)'%@visit(node.value)

    do_Slice: (node) ->
        (lower, upper, step)=('', '', '')
        if getattr(node,'lower',None) is not None:
            lower=@visit(node.lower)
        if getattr(node,'upper',None) is not None:
            upper=@visit(node.upper)
        if getattr(node,'step',None) is not None:
            step=@visit(node.step)
        if step:
            return '%s:%s:%s'%(lower, upper, step)
        else:
            return '%s:%s'%(lower, upper)

    do_Str: (node) ->
        '''A string constant, including docstrings.'''
        if hasattr(node,'lineno'):
            return @sync_string(node)
        else:
            g.trace('==== no lineno',node.s)
            return node.s
    # Subscript(expr value, slice slice, expr_context ctx)

    do_Subscript: (node) ->
        value=@visit(node.value)
        the_slice=@visit(node.slice)
        return '%s[%s]'%(value, the_slice)

    do_Tuple: (node) ->
        elts=@visit(z) for z in node.elts
        return '(%s)'%', '.join(elts)
    #
    # CoffeeScriptTraverser operators...
    #

    op_name: (node, strict=True) ->
        '''Return the print name of an operator node.'''
        d={'Add':'+', 'BitAnd':'&', 'BitOr':'|', 'BitXor':'^', 'Div':'/', 'FloorDiv':'//', 'LShift':'<<', 'Mod':'%', 'Mult':'*', 'Pow':'**', 'RShift':'>>', 'Sub':'-', 'And':' and ', 'Or':' or ', 'Eq':'==', 'Gt':'>', 'GtE':'>=', 'In':' in ', 'Is':' is ', 'IsNot':' is not ', 'Lt':'<', 'LtE':'<=', 'NotEq':'!=', 'NotIn':' not in ', 'AugLoad':'<AugLoad>', 'AugStore':'<AugStore>', 'Del':'<Del>', 'Load':'<Load>', 'Param':'<Param>', 'Store':'<Store>', 'Invert':'~', 'Not':' not ', 'UAdd':'+', 'USub':'-'}
            # Binary operators.
            # Boolean operators.
            # Comparison operators
            # Context operators.
            # Unary operators.
        kind=node.__class__.__name__
        name=d.get(kind,'<%s>'%kind)
        if strict:
            assert name, kind
        return name

    do_BinOp: (node) ->
        return '%s%s%s'%(@visit(node.left), @op_name(node.op), @visit(node.right))

    do_BoolOp: (node) ->
        op_name=@op_name(node.op)
        values=@visit(z) for z in node.values
        return op_name.join(values)

    do_Compare: (node) ->
        result=[]
        lt=@visit(node.left)
        ops=@op_name(z) for z in node.ops
        comps=@visit(z) for z in node.comparators
        result.append(lt)
        if len(ops)==len(comps):
            for i in range(len(ops)):
                result.append('%s%s'%(ops[i], comps[i]))
        else:
            print(('can not happen: ops', repr(ops), 'comparators', repr(comps)))
        return ''.join(result)

    do_IfExp: (node) ->
        return '%s if %s else %s '%(@visit(node.body), @visit(node.test), @visit(node.orelse))

    do_UnaryOp: (node) ->
        return '%s%s'%(@op_name(node.op), @visit(node.operand))
    #
    # CoffeeScriptTraverser statements...
    #

    do_Assert: (node) ->
        leading=@leading_lines(node)
        test=@visit(node.test)
        if getattr(node,'msg',None) is not None:
            s='assert %s, %s\n'%(test, @visit(node.msg))
        else:
            s='assert %s\n'%test
        return ''.join(leading)+@indent(s)

    do_Assign: (node) ->
        leading=@leading_lines(node)
        s='%s=%s\n'%('='.join(@visit(z) for z in node.targets), @visit(node.value))
        return ''.join(leading)+@indent(s)

    do_AugAssign: (node) ->
        op=@op_name(node.op)
        leading=@leading_lines(node)
        target=@visit(node.target)
        value=@visit(node.value)
        s='%s%s=%s\n'%(target, op, value)
        return ''.join(leading)+@indent(s)

    do_Break: (node) ->
        leading=@leading_lines(node)
        return ''.join(leading)+@indent('break\n')

    do_Continue: (node) ->
        leading=@leading_lines(node)
        return ''.join(leading)+@indent('continue\n')

    do_Delete: (node) ->
        leading=@leading_lines(node)
        targets=@visit(z) for z in node.targets
        s='del %s\n'%','.join(targets)
        return ''.join(leading)+@indent(s)

    do_ExceptHandler: (node) ->
        result=@leading_lines(node)
        result.append(@indent('except'))
        if getattr(node,'type',None):
            result.append(' %s'%@visit(node.type))
        if getattr(node,'name',None):
            if isinstance(node.name,ast.AST):
                result.append(' as %s'%@visit(node.name))
            else:
                result.append(' as %s'%node.name)
        result.append(':\n')
        for z in node.body:
            @level+=1
            result.append(@visit(z))
            @level-=1
        return ''.join(result)
    # Python 2.x only

    do_Exec: (node) ->
        leading=@leading_lines(node)
        body=@visit(node.body)
        args=[]
        if getattr(node,'globals',None):
            args.append(@visit(node.globals))
        if getattr(node,'locals',None):
            args.append(@visit(node.locals))
        if args:
            s='exec %s in %s\n'%(body, ','.join(args))
        else:
            s='exec %s\n'%body
        return ''.join(leading)+@indent(s)

    do_For: (node) ->
        result=@leading_lines(node)
        result.append(@indent('for %s in %s:\n'%(@visit(node.target), @visit(node.iter))))
        for z in node.body:
            @level+=1
            result.append(@visit(z))
            @level-=1
        if node.orelse:
            result.append(@indent('else:\n'))
            for z in node.orelse:
                @level+=1
                result.append(@visit(z))
                @level-=1
        return ''.join(result)

    do_Global: (node) ->
        leading=@leading_lines(node)
        s='global %s\n'%','.join(node.names)
        return ''.join(leading)+@indent(s)

    do_If: (node) ->
        result=@leading_lines(node)
        result.append(@indent('if %s:\n'%@visit(node.test)))
        for z in node.body:
            @level+=1
            result.append(@visit(z))
            @level-=1
        if node.orelse:
            result.append(@indent('else:\n'))
            for z in node.orelse:
                @level+=1
                result.append(@visit(z))
                @level-=1
        return ''.join(result)

    do_Import: (node) ->
        leading=@leading_lines(node)
        names=[]
        for (fn, asname) in @get_import_names(node):
            if asname:
                names.append('%s as %s'%(fn, asname))
            else:
                names.append(fn)
        s='import %s\n'%','.join(names)
        s='pass # '+s
        return ''.join(leading)+@indent(s)

    get_import_names: (node) ->
        '''Return a list of the the full file names in the import statement.'''
        result=[]
        for ast2 in node.names:
            assert isinstance(ast2,ast.alias)
            data=(ast2.name, ast2.asname)
            result.append(data)
        return result

    do_ImportFrom: (node) ->
        leading=@leading_lines(node)
        names=[]
        for (fn, asname) in @get_import_names(node):
            if asname:
                names.append('%s as %s'%(fn, asname))
            else:
                names.append(fn)
        s='from %s import %s\n'%(node.module, ','.join(names))
        s='pass # '+s
        return ''.join(leading)+@indent(s)

    do_Pass: (node) ->
        leading=@leading_lines(node)
        return ''.join(leading)+@indent('pass\n')
    # Python 2.x only

    do_Print: (node) ->
        leading=@leading_lines(node)
        vals=[]
        for z in node.values:
            vals.append(@visit(z))
        if getattr(node,'dest',None) is not None:
            vals.append('dest=%s'%@visit(node.dest))
        if getattr(node,'nl',None) is not None:
            if node.nl=='False':
                vals.append('nl=%s'%node.nl)
        s='print(%s)\n'%','.join(vals)
        return ''.join(leading)+@indent(s)

    do_Raise: (node) ->
        leading=@leading_lines(node)
        args=[]
        for attr in ('type', 'inst', 'tback'):
            if getattr(node,attr,None) is not None:
                args.append(@visit(getattr(node,attr)))
        if args:
            s='raise %s\n'%', '.join(args)
        else:
            s='raise\n'
        return ''.join(leading)+@indent(s)

    do_Return: (node) ->
        leading=@leading_lines(node)
        if node.value:
            s='return %s\n'%@visit(node.value).strip()
        else:
            s='return\n'
        return ''.join(leading)+@indent(s)
    # Try(stmt* body, excepthandler* handlers, stmt* orelse, stmt* finalbody)

    do_Try: (node) ->
        result=@leading_lines(node)
        result.append(@indent('try:\n'))
        for z in node.body:
            @level+=1
            result.append(@visit(z))
            @level-=1
        if node.handlers:
            for z in node.handlers:
                result.append(@visit(z))
        if node.orelse:
            result.append(@indent('else:\n'))
            for z in node.orelse:
                @level+=1
                result.append(@visit(z))
                @level-=1
        if node.finalbody:
            result.append(@indent('finally:\n'))
            for z in node.finalbody:
                @level+=1
                result.append(@visit(z))
                @level-=1
        return ''.join(result)

    do_TryExcept: (node) ->
        result=@leading_lines(node)
        result.append(@indent('try:\n'))
        for z in node.body:
            @level+=1
            result.append(@visit(z))
            @level-=1
        if node.handlers:
            for z in node.handlers:
                result.append(@visit(z))
        if node.orelse:
            result.append('else:\n')
            for z in node.orelse:
                @level+=1
                result.append(@visit(z))
                @level-=1
        return ''.join(result)

    do_TryFinally: (node) ->
        result=@leading_lines(node)
        result.append(@indent('try:\n'))
        for z in node.body:
            @level+=1
            result.append(@visit(z))
            @level-=1
        result.append(@indent('finally:\n'))
        for z in node.finalbody:
            @level+=1
            result.append(@visit(z))
            @level-=1
        return ''.join(result)

    do_While: (node) ->
        result=@leading_lines(node)
        result.append(@indent('while %s:\n'%@visit(node.test)))
        for z in node.body:
            @level+=1
            result.append(@visit(z))
            @level-=1
        if node.orelse:
            result.append('else:\n')
            for z in node.orelse:
                @level+=1
                result.append(@visit(z))
                @level-=1
        return ''.join(result)

    do_With: (node) ->
        result=@leading_lines(node)
        result.append(@indent('with '))
        if hasattr(node,'context_expression'):
            result.append(@visit(node.context_expresssion))
        vars_list=[]
        if hasattr(node,'optional_vars'):
            try:
                for z in node.optional_vars:
                    vars_list.append(@visit(z))
            except TypeError:
                vars_list.append(@visit(node.optional_vars))
        result.append(','.join(vars_list))
        result.append(':\n')
        for z in node.body:
            @level+=1
            result.append(@visit(z))
            @level-=1
        result.append('\n')
        return ''.join(result)

    do_Yield: (node) ->
        leading=@leading_lines(node)
        if getattr(node,'value',None) is not None:
            s='yield %s\n'%@visit(node.value)
        else:
            s='yield\n'
        return ''.join(leading)+@indent(s)


class LeoGlobals extends object
    '''A class supporting g.pdb and g.trace for compatibility with Leo.'''


    class NullObject
        """
        An object that does nothing, and does it very well.
        From the Python cookbook, recipe 5.23
        """

        __init__: (*args, **keys) ->
            pass

        __call__: (*args, **keys) ->
            return @

        __repr__: ->
            return "NullObject"

        __str__: ->
            return "NullObject"

        __bool__: ->
            return False

        __nonzero__: ->
            return 0

        __delattr__: (attr) ->
            return @

        __getattr__: (attr) ->
            return @

        __setattr__: (attr, val) ->
            return @


    class ReadLinesClass
        """A class whose next method provides a readline method for Python's tokenize module."""

        __init__: (s) ->
            @lines=s.splitlines(True) if s else [] 
                # g.splitLines(s)
            @i=0

        next: ->
            if @i<len(@lines):
                line=@lines[@i]
                @i+=1
            else:
                line=''
            # g.trace(repr(line))
            return line
        __next__=next

    _callerName: (n=1, files=False) ->
        # print('_callerName: %s %s' % (n,files))
        try:
            f1=sys._getframe(n)
            code1=f1.f_code
            name=code1.co_name
            if name=='__init__':
                name='__init__(%s,line %s)'%(@shortFileName(code1.co_filename), code1.co_firstlineno)
            if files:
                return '%s:%s'%(@shortFileName(code1.co_filename), name)
            else:
                return name
        except ValueError:
            # print('g._callerName: ValueError',n)
            return ''
        except Exception:
            # es_exception()
            return ''

    callers: (n=4, count=0, excludeCaller=True, files=False) ->
        '''Return a list containing the callers of the function that called g.callerList.

        If the excludeCaller keyword is True (the default), g.callers is not on the list.

        If the files keyword argument is True, filenames are included in the list.
        '''
        # sys._getframe throws ValueError in both cpython and jython if there are less than i entries.
        # The jython stack often has less than 8 entries,
        # so we must be careful to call g._callerName with smaller values of i first.
        result=[]
        i=3 if excludeCaller else 2 
        while 1:
            s=@_callerName(i,files=files)
            # print(i,s)
            if s:
                result.append(s)
            if  not s or len(result)>=n:
                break
            i+=1
        result.reverse()
        if count>0:
            result=result[:count]
        sep='\n' if files else ',' 
        return sep.join(result)

    cls: ->
        '''Clear the screen.'''
        if sys.platform.lower().startswith('win'):
            os.system('cls')

    computeLeadingWhitespace: (width, tab_width) ->
        '''Returns optimized whitespace corresponding to width with the indicated tab_width.'''
        if width<=0:
            return ""
        else:
            if tab_width>1:
                tabs=int(width/tab_width)
                blanks=int(width%tab_width)
                return '\t'*tabs+' '*blanks
            else:
                return ' '*width

    computeLeadingWhitespaceWidth: (s, tab_width) ->
        '''Returns optimized whitespace corresponding to width with the indicated tab_width.'''
        w=0
        for ch in s:
            if ch==' ':
                w+=1
            else:
                if ch=='\t':
                    w+=abs(tab_width)-w%abs(tab_width)
                else:
                    break
        return w

    isString: (s) ->
        '''Return True if s is any string, but not bytes.'''
        if isPython3:
            return type(s)==type('a')
        else:
            return type(s) in types.StringTypes

    isUnicode: (s) ->
        '''Return True if s is a unicode string.'''
        if isPython3:
            return type(s)==type('a')
        else:
            return type(s)==types.UnicodeType

    pdb: ->
        try:
            pass # import leo.core.leoGlobals as leo_g
            leo_g.pdb()
        except ImportError:
            pass # import pdb
            pdb.set_trace()

    shortFileName: (fileName, n=None) ->
        if n is None or n<1:
            return os.path.basename(fileName)
        else:
            return '/'.join(fileName.replace('\\','/').split('/')[-n:])

    splitLines: (s) ->
        '''Split s into lines, preserving trailing newlines.'''
        return s.splitlines(True) if s else []

    toUnicode: (s, encoding='utf-8', reportErrors=False) ->
        '''Connvert a non-unicode string with the given encoding to unicode.'''
        trace=False
        if g.isUnicode(s):
            return s
        if  not encoding:
            encoding='utf-8'
        # These are the only significant calls to s.decode in Leo.
        # Tracing these calls directly yields thousands of calls.
        # Never call g.trace here!
        try:
            s=s.decode(encoding,'strict')
        except UnicodeError:
            s=s.decode(encoding,'replace')
            if trace or reportErrors:
                g.trace(g.callers())
                print("toUnicode: Error converting %s... from %s encoding to unicode"%(s[:200], encoding))
        except AttributeError:
            if trace:
                print('toUnicode: AttributeError!: %s'%s)
            # May be a QString.
            s=g.u(s)
        if trace and encoding=='cp1252':
            print('toUnicode: returns %s'%s)
        return s

    trace: (*args, **keys) ->
        try:
            pass # import leo.core.leoGlobals as leo_g
            leo_g.trace(caller_level=2,*args,**keys)
        except ImportError:
            print((args, keys))
    if isPython3:

        u: (s) ->
            return s

        ue: (s, encoding) ->
            return s if g.isUnicode(s) else str(s,encoding)
    else:

        u: (s) ->
            return unicode(s)

        ue: (s, encoding) ->
            return unicode(s,encoding)


class MakeCoffeeScriptController extends object
    '''The controller class for python_to_coffeescript.py.'''

    __init__: ->
        '''Ctor for MakeCoffeeScriptController class.'''
        @options={}
        # Ivars set on the command line...
        @config_fn=None
        @enable_unit_tests=False
        @files=[]
        @section_names=('Global')
        # Ivars set in the config file...
        @output_directory=@finalize('.')
        @overwrite=False
        @verbose=False

    finalize: (fn) ->
        '''Finalize and regularize a filename.'''
        fn=os.path.expanduser(fn)
        fn=os.path.abspath(fn)
        fn=os.path.normpath(fn)
        return fn

    make_coffeescript_file: (fn) ->
        '''
        Make a stub file in the output directory for all source files mentioned
        in the [Source Files] section of the configuration file.
        '''
        if  not fn.endswith('.py'):
            print(('not a python file', fn))
            return
        if  not os.path.exists(fn):
            print(('not found', fn))
            return
        base_fn=os.path.basename(fn)
        out_fn=os.path.join(@output_directory,base_fn)
        out_fn=os.path.normpath(out_fn)
        out_fn=out_fn[:-3]+'.coffee'
        dir_=os.path.dirname(out_fn)
        if os.path.exists(out_fn) and  not @overwrite:
            print('file exists: %s'%out_fn)
        else:
            if  not dir_ or os.path.exists(dir_):
                t1=time.clock()
                s=open(fn).read()
                readlines=g.ReadLinesClass(s).next
                tokens=list(tokenize.generate_tokens(readlines))
            # s = CoffeeScriptTokenizer(controller=self).format(tokens)
                node=ast.parse(s,filename=fn,mode='exec')
                s=CoffeeScriptTraverser(controller=@).format(node,s,tokens)
                f=open(out_fn,'w')
                @output_time_stamp(f)
                f.write(s)
                f.close()
                print('wrote: %s'%out_fn)
            else:
                print('output directory not not found: %s'%dir_)

    output_time_stamp: (f) ->
        '''Put a time-stamp in the output file f.'''
        f.write('# python_to_coffeescript: %s\n'%time.strftime("%a %d %b %Y at %H:%M:%S"))

    run: ->
        '''
        Make stub files for all files.
        Do nothing if the output directory does not exist.
        '''
        if @enable_unit_tests:
            @run_all_unit_tests()
        if @files:
            dir_=@output_directory
            if dir_:
                if os.path.exists(dir_):
                    for fn in @files:
                        @make_coffeescript_file(fn)
                else:
                    print('output directory not found: %s'%dir_)
            else:
                print('no output directory')
        else:
            if  not @enable_unit_tests:
                print('no input files')

    run_all_unit_tests: ->
        '''Run all unit tests in the python-to-coffeescript/test directory.'''
        pass # import unittest
        loader=unittest.TestLoader()
        suite=loader.discover(os.path.abspath('.'),pattern='test*.py',top_level_dir=None)
        unittest.TextTestRunner(verbosity=1).run(suite)

    scan_command_line: ->
        '''Set ivars from command-line arguments.'''
        # This automatically implements the --help option.
        usage="usage: python_to_coffeescript.py [options] file1, file2, ..."
        parser=optparse.OptionParser(usage=usage)
        add=parser.add_option
        add('-c','--config',dest='fn',help='full path to configuration file')
        add('-d','--dir',dest='dir',help='full path to the output directory')
        add('-o','--overwrite',action='store_true',default=False,help='overwrite existing .coffee files')
        # add('-t', '--test', action='store_true', default=False,
            # help='run unit tests on startup')
        add('-v','--verbose',action='store_true',default=False,help='verbose output')
        # Parse the options
        (options, args)=parser.parse_args()
        # Handle the options...
        # self.enable_unit_tests = options.test
        @overwrite=options.overwrite
        if options.fn:
            @config_fn=options.fn
        if options.dir:
            dir_=options.dir
            dir_=@finalize(dir_)
            if os.path.exists(dir_):
                @output_directory=dir_
            else:
                print('--dir: directory does not exist: %s'%dir_)
                print('exiting')
                sys.exit(1)
        # If any files remain, set self.files.
        if args:
            args=@finalize(z) for z in args
            if args:
                @files=args

    scan_options: ->
        '''Set all configuration-related ivars.'''
        trace=False
        if  not @config_fn:
            return
        @parser=parser=@create_parser()
        s=@get_config_string()
        @init_parser(s)
        if @files:
            files_source='command-line'
            files=@files
        else:
            if parser.has_section('Global'):
                files_source='config file'
                files=parser.get('Global','files')
                files=z.strip() for z in files.split('\n') if z.strip()
            else:
                return
        files2=[]
        for z in files:
            files2.extend(glob.glob(@finalize(z)))
        @files=z for z in files2 if z and os.path.exists(z)
        if trace:
            print('Files (from %s)...\n'%files_source)
            for z in @files:
                print(z)
            print('')
        if 'output_directory' in parser.options('Global'):
            s=parser.get('Global','output_directory')
            output_dir=@finalize(s)
            if os.path.exists(output_dir):
                @output_directory=output_dir
                if @verbose:
                    print('output directory: %s\n'%output_dir)
            else:
                print('output directory not found: %s\n'%output_dir)
                @output_directory=None
        if 'prefix_lines' in parser.options('Global'):
            prefix=parser.get('Global','prefix_lines')
            @prefix_lines=prefix.split('\n')
                # The parser does not preserve leading whitespace.
            if trace:
                print('Prefix lines...\n')
                for z in @prefix_lines:
                    print(z)
                print('')
        #
        # self.def_patterns = self.scan_patterns('Def Name Patterns')
        # self.general_patterns = self.scan_patterns('General Patterns')
        # self.make_patterns_dict()

    create_parser: ->
        '''Create a RawConfigParser and return it.'''
        parser=configparser.RawConfigParser()
        parser.optionxform=str
        return parser

    get_config_string: ->
        fn=@finalize(@config_fn)
        if os.path.exists(fn):
            if @verbose:
                print('\nconfiguration file: %s\n'%fn)
            f=open(fn,'r')
            s=f.read()
            f.close()
            return s
        else:
            print('\nconfiguration file not found: %s'%fn)
            return ''

    init_parser: (s) ->
        '''Add double back-slashes to all patterns starting with '['.'''
        trace=False
        if  not s:
            return
        aList=[]
        for s in s.split('\n'):
            if @is_section_name(s):
                aList.append(s)
            else:
                if s.strip().startswith('['):
                    aList.append(r'\\'+s[1:])
                    if trace:
                        g.trace('*** escaping:',s)
                else:
                    aList.append(s)
        s='\n'.join(aList)+'\n'
        if trace:
            g.trace(s)
        file_object=io.StringIO(s)
        @parser.readfp(file_object)

    is_section_name: (s) ->

        munge: (s) ->
            return s.strip().lower().replace(' ','')
        s=s.strip()
        if s.startswith('[') and s.endswith(']'):
            s=munge(s[1:-1])
            for s2 in @section_names:
                if s==munge(s2):
                    return True
        return False


class ParseState extends object
    '''A class representing items parse state stack.'''

    __init__: (kind, value) ->
        @kind=kind
        @value=value

    __repr__: ->
        return 'State: %10s %s'%(@kind, repr(@value))
    __str__=__repr__


class TokenSync extends object
    '''A class to sync and remember tokens.'''
    # To do: handle comments, line breaks...

    __init__: (s, tokens) ->
        '''Ctor for TokenSync class.'''
        assert isinstance(tokens,list)
        @s=s
        @first_leading_line=None
        @lines=z.rstrip() for z in g.splitLines(s)
        @line_tokens=@make_line_tokens(tokens)
        @string_tokens=@make_string_tokens()
        @comment_lines=@make_comment_lines()

    make_comment_lines: ->
        '''Return a copy of line_tokens containing only full-line comments.'''
        result=[]
        for aList in @line_tokens:
            aList2=z for z in aList if @is_line_comment(z)
            assert len(aList2)<2
            result.append(aList2[0] if aList2 else None )
        assert len(result)==len(@line_tokens)
        for (i, aList) in enumerate(result):
            if aList:
                @first_leading_line=i
                break
        else:
            @first_leading_line=len(result)
        return result

    make_line_tokens: (tokens) ->
        '''
        Return a list of lists of tokens for each list in self.lines.
        The strings in self.lines may end in a backslash, so care is needed.
        '''
        trace=False
        (n, result)=(len(@lines), [])
        for i in range(0,n+1):
            result.append([])
        for token in tokens:
            (t1, t2, t3, t4, t5)=token
            kind=token_module.tok_name[t1].lower()
            (srow, scol)=t3
            (erow, ecol)=t4
            line=erow-1 if kind=='string' else srow-1 
            result[line].append(token)
            if trace:
                g.trace('%3s %s'%(line, @dump_token(token)))
        assert len(@lines)+1==len(result), len(result)
        return result

    make_string_tokens: ->
        '''Return a copy of line_tokens containing only string tokens.'''
        result=[]
        for aList in @line_tokens:
            result.append(z for z in aList if @token_type(z)=='string')
        assert len(result)==len(@line_tokens)
        return result

    dump_token: (token) ->
        '''Dump the token for debugging.'''
        (t1, t2, t3, t4, t5)=token
        kind=g.toUnicode(token_module.tok_name[t1].lower())
        raw_val=g.toUnicode(t5)
        val=g.toUnicode(t2)
        return 'token: %10s %r'%(kind, val)

    is_line_comment: (token) ->
        '''Return True if the token represents a full-line comment.'''
        (t1, t2, t3, t4, t5)=token
        kind=token_module.tok_name[t1].lower()
        raw_val=t5
        return kind=='comment' and raw_val.lstrip().startswith('#')

    leading_lines: (node) ->
        '''Return a list of the preceding comment and blank lines'''
        # This can be called on arbitrary nodes.
        trace=False
        leading=[]
        if hasattr(node,'lineno'):
            (i, n)=(@first_leading_line, node.lineno)
            while i<n:
                token=@comment_lines[i]
                if token:
                    s=@token_raw_val(token).rstrip()+'\n'
                    leading.append(s)
                    if trace:
                        g.trace('%11s: %s'%(i, s.rstrip()))
                i+=1
            @first_leading_line=i
        return leading

    line_at: (node, continued_lines=True) ->
        '''Return the lines at the node, possibly including continuation lines.'''
        n=getattr(node,'lineno',None)
        if n is None:
            return '<no line> for %s'%node.__class__.__name__
        else:
            if continued_lines:
                (aList, n)=([], n-1)
                while n<len(@lines):
                    s=@lines[n]
                    if s.endswith('\\'):
                        aList.append(s[:-1])
                        n+=1
                    else:
                        aList.append(s)
                        break
                return ''.join(aList)
            else:
                return @lines[n-1]

    sync_string: (node) ->
        '''Return the spelling of the string at the given node.'''
        # g.trace('%-10s %2s: %s' % (' ', node.lineno, self.line_at(node)))
        n=node.lineno
        tokens=@string_tokens[n-1]
        if tokens:
            token=tokens.pop(0)
            @string_tokens[n-1]=tokens
            return @token_val(token)
        else:
            g.trace('===== underflow',n,node.s)
            return node.s

    token_type: (token) ->
        '''Return the token's type.'''
        (t1, t2, t3, t4, t5)=token
        return g.toUnicode(token_module.tok_name[t1].lower())

    token_raw_val: (token) ->
        '''Return the value of the token.'''
        (t1, t2, t3, t4, t5)=token
        return g.toUnicode(t5)

    token_val: (token) ->
        '''Return the raw value of the token.'''
        (t1, t2, t3, t4, t5)=token
        return g.toUnicode(t2)
g=LeoGlobals()
if __name__=="__main__":
    main()

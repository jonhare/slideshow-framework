from abc import abstractmethod

from kivy.properties import ListProperty, StringProperty, NumericProperty
from kivy.resources import resource_find
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.codeinput import CodeInput
from kivy.uix.splitter import Splitter
from pygments.lexers import PythonLexer

from . import Slide
from .shells.python_shell import PythonREPLWidget
from .shells.simple_cmd_shell import ShellConsole


class __AbstractShellSlide(Slide):
    foreground_color = ListProperty((0, 0, 0, 1))
    background_color = ListProperty((1, 1, 1, 1))
    font_name = StringProperty('RobotoMono-regular')
    font_size = NumericProperty("14sp")

    def __init__(self, **kw):
        super().__init__(**kw)

    def build(self):
        layout = BoxLayout(size_hint=(0.98, 0.98), pos_hint={'x': 0.01, 'y': 0.01})

        ci, tis = self.get_shell()

        for ti in tis:
            ti.bind(focus=self.text_area_on_focus)

        self.bind(font_name=ci.setter('font_name'))
        self.bind(font_size=ci.setter('font_size'))
        self.bind(background_color=ci.setter('background_color'))
        self.bind(foreground_color=ci.setter('foreground_color'))

        self.property('font_name').dispatch(self)
        self.property('font_size').dispatch(self)
        self.property('background_color').dispatch(self)
        self.property('foreground_color').dispatch(self)

        layout.add_widget(ci)

        self.add_widget(layout)

    def text_area_on_focus(self, instance, value, *args):
        self.ignore_keyboard = value

    @abstractmethod
    def get_shell(self):
        pass


class PythonREPLSlide(__AbstractShellSlide):
    def get_shell(self):
        ci = PythonREPLWidget(size_hint=(0.9, 0.9))
        return ci, [ci.text_input]


class TerminalSlide(__AbstractShellSlide):
    def get_shell(self):
        ci = ShellConsole(size_hint=(0.9, 0.9))
        return ci, [ci.console_input]


class PythonCodeREPLSlide(Slide):
    def __init__(self, initial_script="", initial_script_file=None, **kwargs):
        super().__init__(**kwargs)

        self.shell = None
        self.initial_script = initial_script

        if initial_script_file:
            with open(resource_find(initial_script_file), 'r') as file:
                self.initial_script += file.read()

    def build(self):
        layout = BoxLayout(size_hint=(0.98, 0.98), pos_hint={'x': 0.01, 'y': 0.01})

        splitter = Splitter(sizable_from='right')
        ci = CodeInput(lexer=PythonLexer())
        ci.bind(focus=self.text_area_on_focus)
        ci.bind(focus=self.rerun_code)

        splitter.add_widget(ci)
        layout.add_widget(splitter)

        repl = PythonREPLWidget(banner=False)
        self.shell = repl.sh
        if len(self.initial_script.strip()) > 0:
            self.shell.runcode(self.initial_script)
            ci.text = self.initial_script

        repl.text_input.bind(focus=self.text_area_on_focus)
        layout.add_widget(repl)

        self.add_widget(layout)

    def rerun_code(self, instance, value, *args):
        if value is False:
            self.shell.runcode(instance.text)

    def text_area_on_focus(self, instance, value, *args):
        self.ignore_keyboard = value

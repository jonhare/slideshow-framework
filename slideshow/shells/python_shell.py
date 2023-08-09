import code
import sys
import threading

from kivy.base import runTouchApp
from kivy.clock import Clock
from kivy.config import Config
from kivy.properties import ListProperty, NumericProperty, StringProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput

Config.set('kivy', 'exit_on_escape', '0')


class PseudoFile(object):

    def __init__(self, sh):
        self.sh = sh

    def write(self, s):
        self.sh.write(s)

    def writelines(self, lines):
        for line in lines:
            self.write(line)

    def flush(self):
        pass

    def isatty(self):
        return True


class Shell(code.InteractiveConsole):
    "Wrapper around Python that can filter input/output to the shell"

    def __init__(self, root):
        code.InteractiveConsole.__init__(self)
        self.thread = None
        self.root = root

    def write(self, data):
        import functools
        Clock.schedule_once(functools.partial(self.root.show_output, data), 0)

    def push(self, line):
        return code.InteractiveConsole.push(self, line)

    def raw_input(self, prompt="") -> str | bytes:
        return self.root.get_input(prompt)

    def runcode(self, code):
        """Execute a code object.

        When an exception occurs, self.showtraceback() is called to
        display a traceback.  All exceptions are caught except
        SystemExit, which is reraised.

        A note about KeyboardInterrupt: this exception may occur
        elsewhere in this code, and may not always be caught.  The
        caller should be prepared to deal with it.

        """
        org_stdout = sys.stdout
        sys.stdout = PseudoFile(self)
        try:
            exec(code, self.locals)
        except SystemExit:
            raise
        except:
            self.showtraceback()
        finally:
            sys.stdout = org_stdout

    def interact(self, banner=None, _=None):
        """Closely emulate the interactive Python console.

        The optional banner argument specify the banner to print
        before the first interaction; by default it prints a banner
        similar to the one printed by the real Python interpreter,
        followed by the current class name in parentheses (so as not
        to confuse this with the real interpreter -- since it's so
        close!).

        """
        try:
            sys.ps1
        except AttributeError:
            sys.ps1 = ">>> "
        try:
            sys.ps2
        except AttributeError:
            sys.ps2 = "... "
        cprt = 'Type "help", "copyright", "credits" or "license" for more information.'
        if banner is None:
            self.write("Python %s on %s\n%s\n(%s)\n" %
                       (sys.version, sys.platform, cprt,
                        self.__class__.__name__))
        elif banner is not False:
            self.write("%s\n" % str(banner))
        more = 0
        while 1:
            try:
                if more:
                    prompt = sys.ps2
                else:
                    prompt = sys.ps1
                try:
                    line = self.raw_input(prompt)
                    # Can be None if sys.stdin was redefined
                    encoding = getattr(sys.stdin, "encoding", None)
                    if encoding and not isinstance(line, str):
                        line = line.decode(encoding)
                except EOFError:
                    self.write("\n")
                    break
                else:
                    more = self.push(line)
            except KeyboardInterrupt:
                self.write("\nKeyboardInterrupt\n")
                self.resetbuffer()
                more = 0


class InteractiveThread(threading.Thread):

    def __init__(self, sh, banner):
        super(InteractiveThread, self).__init__()
        self._sh = sh
        self._sh.thread = self
        self.daemon = True
        self.banner = banner

    def run(self):
        self._sh.interact(self.banner)


class InteractiveShellInput(TextInput):
    __events__ = ('on_ready_to_input',)

    def __init__(self, history=None, **kwargs):
        super(InteractiveShellInput, self).__init__(**kwargs)
        self.last_line = None

        if history is None:
            history = []
        self.history = history
        self.history_index = len(self.history)

    def keyboard_on_key_down(self, window, keycode, text, modifiers):
        if keycode[1] == 'left':
            if self.cursor_index() <= self._cursor_pos:
                return False

        if keycode[1] == 'up':
            self.history_index -= 1
            if self.history_index < 0:
                self.history_index = 0

            if len(self.history) > 0:
                self.text = self.text[0:self._cursor_pos]
                self.text += self.history[self.history_index]
            return False

        if keycode[1] == 'down':
            self.history_index += 1
            if self.history_index > len(self.history):
                self.history_index = len(self.history)

            if len(self.history) > 0:
                self.text = self.text[0:self._cursor_pos]
                if self.history_index < len(self.history):
                    self.text += self.history[self.history_index]
            return False

        if keycode[0] == 13:
            # For enter
            self.last_line = self.text[self._cursor_pos:]
            self.history.append(self.last_line)
            self.history_index = len(self.history)
            self.dispatch('on_ready_to_input')

        return super(InteractiveShellInput, self).keyboard_on_key_down(window, keycode, text, modifiers)

    def on_ready_to_input(self, *args):
        pass

    def show_output(self, output):
        self.text += output
        Clock.schedule_once(self._set_cursor_val, 0)

    def _set_cursor_val(self, *args):
        self._cursor_pos = self.cursor_index()


class PythonREPLWidget(BoxLayout):
    foreground_color = ListProperty((0, 0, 0, 1))
    '''This defines the color of the text in the console
    '''

    background_color = ListProperty((1, 1, 1, 1))
    '''This defines the color of the text in the console
    '''

    font_name = StringProperty('RobotoMono-regular')
    '''Indicates the font Style used in the console
    '''

    font_size = NumericProperty("14sp")
    '''Indicates the size of the font used for the console
    '''

    def __init__(self, banner=None, history=None, **kwargs):
        super(PythonREPLWidget, self).__init__()

        self.text_input = InteractiveShellInput(history)
        self.text_input.bind(on_ready_to_input=self.ready_to_input)
        self.bind(font_name=self.text_input.setter('font_name'))
        self.bind(font_size=self.text_input.setter('font_size'))
        self.bind(background_color=self.text_input.setter('background_color'))
        self.bind(foreground_color=self.text_input.setter('foreground_color'))

        self.property('font_name').dispatch(self)
        self.property('font_size').dispatch(self)
        self.property('background_color').dispatch(self)
        self.property('foreground_color').dispatch(self)

        self.add_widget(self.text_input)
        self.sh = Shell(self)
        self._thread = InteractiveThread(self.sh, banner)

        Clock.schedule_once(self.run_sh, -1)
        self._ready_to_input = False

        self.prompt = None

    def ready_to_input(self, *args):
        self._ready_to_input = True

    def run_sh(self, *args):
        self._thread.start()

    def show_output(self, data, dt):
        self.text_input.show_output(data)

    def _show_prompt(self, *args):
        self.text_input.show_output(self.prompt)

    def get_input(self, prompt):
        import time
        self.prompt = prompt
        Clock.schedule_once(self._show_prompt, 0.1)
        while not self._ready_to_input:
            time.sleep(0.1)

        self._ready_to_input = False
        return self.text_input.last_line


if __name__ == '__main__':
    runTouchApp(PythonREPLWidget())

import os
import os
import shlex
import subprocess
import sys
import threading

from kivy.base import runTouchApp
from kivy.clock import mainthread
from kivy.event import EventDispatcher
from kivy.lang import Builder
from kivy.properties import ObjectProperty, ListProperty, StringProperty, \
    NumericProperty, Clock, partial
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput

# TODO:
#  support for terminal emulation using pyte - requires rethinking the gui a bit and customising scrolling
#       (basically a fixed size text area, custom scroll bars and touch events & call into pyte for the data)
#  support for interactive sessions (requires terminal emulation and opening a persistent process [like bash])
#  history (maybe we get that for free with an actual shell?!)


Builder.load_string('''
<ShellConsole>:
    console_input: console_input
    scroll_view: scroll_view
    ScrollView:
        id: scroll_view
        scroll_y: 0
        ShellConsoleInput:
            id: console_input
            shell: root
            size_hint: (1, None)
            font_name: root.font_name
            font_size: root.font_size
            foreground_color: root.foreground_color
            background_color: root.background_color
            height: max(self.parent.height, self.minimum_height)
''')


def threaded(fn):
    def wrapper(*args, **kwargs):
        th = threading.Thread(target=fn, args=args, kwargs=kwargs)
        th.daemon = True
        th.start()

    return wrapper


class Shell(EventDispatcher):
    __events__ = ('on_output', 'on_complete')

    process = ObjectProperty(None)
    '''subprocess process
    '''

    @threaded
    def run_command(self, command, show_output=True, *args):
        output = ''
        try:
            self.process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            for line in iter(self.process.stdout.readline, b""):
                line = line.decode("utf8")
                output += line
                if show_output:
                    self.dispatch('on_output', line)
        except Exception as e:
            line = str(e) + "\n"
            output += line
            if show_output:
                self.dispatch('on_output', line)
        finally:
            self.dispatch('on_complete', output)

    @threaded
    def stop(self, *args):
        if self.process:
            self.process.kill()


class ShellConsoleInput(TextInput):
    '''Displays Output and sends input to Shell. Emits 'on_ready_to_input'
       when it is ready to get input from user.
    '''

    shell = ObjectProperty(None)
    '''Instance of ShellConsole(parent) widget
    '''

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._cursor_pos = 0  # position of the cursor before after prompt
        self.__init_console()

    def __init_console(self, *args):
        '''Create initial values for the prompt and shows it
        '''
        self.cur_dir = os.getcwd()
        self._hostname = 'kivy'
        try:
            if hasattr(os, 'uname'):
                self._hostname = os.uname()[1]
            else:
                self._hostname = os.environ.get('COMPUTERNAME', 'kivy')
        except Exception:
            pass
        self._username = os.environ.get('USER', '')
        if not self._username:
            self._username = os.environ.get('USERNAME', 'designer')
        self.prompt()

    def keyboard_on_key_down(self, window, keycode, text, modifiers):
        self.parent.scroll_y = 0

        if keycode[0] == 13:
            # Enter -> execute the command
            self.validate_cursor_pos()
            text = self.text[self._cursor_pos:]
            if text.strip():
                Clock.schedule_once(partial(self._run_cmd, text))
            else:
                self.on_output("\n")
                self.prompt()
        elif keycode[0] in [8, 127]:
            self.cancel_selection()

        elif keycode[0] == 99 and modifiers == ['ctrl']:
            self.shell.stop()

        if self.cursor_index() < (self._cursor_pos + 1):
            return False

        return super().keyboard_on_key_down(
            window, keycode, text, modifiers)

    def _run_cmd(self, cmd, *args):
        _posix = True
        if sys.platform[0] == 'w':
            _posix = False

        commands = shlex.split(str(cmd), posix=_posix)
        self.shell.run_command(commands)

    def validate_cursor_pos(self, *args):
        if self.cursor_index() < self._cursor_pos:
            self.cursor = self.get_cursor_from_index(self._cursor_pos)

    @mainthread
    def prompt(self, *args):
        '''Show the PS1 variable
        '''
        ps1 = "[%s@%s %s]> " % (
            self._username, self._hostname,
            os.path.basename(str(self.cur_dir)))
        self._cursor_pos = self.cursor_index() + len(ps1)
        self.text += ps1

    @mainthread
    def on_output(self, output):
        self.text += output

    def on_complete(self, output):
        self.prompt()


class ShellConsole(BoxLayout, Shell):
    console_input = ObjectProperty(None)
    '''Instance of ConsoleInput
       :data:`console_input` is an :class:`~kivy.properties.ObjectProperty`
    '''

    scroll_view = ObjectProperty(None)
    '''Instance of :class:`~kivy.uix.scrollview.ScrollView`
       :data:`scroll_view` is an :class:`~kivy.properties.ObjectProperty`
    '''

    foreground_color = ListProperty((0, 0, 0, 1))
    '''This defines the color of the text in the console

    :data:`foreground_color` is an :class:`~kivy.properties.ListProperty`,
    Default to '(.5, .5, .5, .93)'
    '''

    background_color = ListProperty((1, 1, 1, 1))
    '''This defines the color of the text in the console

    :data:`foreground_color` is an :class:`~kivy.properties.ListProperty`,
    Default to '(0, 0, 0, 1)'''

    font_name = StringProperty('RobotoMono-regular')
    '''Indicates the font Style used in the console

    :data:`font` is a :class:`~kivy.properties.StringProperty`,
    Default to 'DroidSansMono'
    '''

    font_size = NumericProperty("14sp")
    '''Indicates the size of the font used for the console

    :data:`font_size` is a :class:`~kivy.properties.NumericProperty`,
    Default to '9'
    '''

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def on_output(self, output):
        '''Event handler to send output data
        '''
        self.console_input.on_output(output)

    def on_complete(self, output):
        '''Event handler to send output data
        '''
        self.console_input.on_complete(output)


if __name__ == '__main__':
    runTouchApp(ShellConsole())

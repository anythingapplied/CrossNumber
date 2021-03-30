test
import re
import json
import collections
import tkinter as tk
import tkinter.font as tkfont
import ctypes

import fitz

import clueframe
import movequeue

#Todo:
# Striping clues (white/gray/white/etc)
# Frame main sections?
# Highlight dependent and parent clues
# Get clue text column width to shrink/enlarge with window size
# Consistent row mode/column mode
# Load not found error
# Click clues
# Scroll clues to display new highlighted clue
# Load file from open application
# Check to make sure it opens without specified number
# Remove dummy

class Colors:
    foreground = 'White'
    blanks = 'Black'
    selected = '#007FC3'
    mouseover = 'LightGray'
    rowselected = '#CCE6F3'
    hints = '#191A17'
    error = 'Red'

class Cell:
    def __init__(self, game, ishead, x, y, text=None):
        self.game = game

        self.ishead = ishead

        self._iserror = False
        self._isselected = False
        self._isrowselected = False
        self._mouseover = False

        self.x = x
        self.y = y
        self.clues = []

        helv1 = tkfont.Font(family='Helvetica', size=7, weight='bold')
        helv2 = tkfont.Font(family='Helvetica', size=6)
        helv3 = tkfont.Font(family='Helvetica', size=18)

        xpixel = self.game.xoff + x*self.game.cellsize
        ypixel = self.game.yoff + y*self.game.cellsize
        self.rect = self.game.board.create_rectangle(
                xpixel,
                ypixel,
                xpixel + self.game.cellsize,
                ypixel + self.game.cellsize,
                fill=Colors.foreground)
        if text:
            self.game.board.create_text(
                xpixel + 1,
                ypixel - 1,
                anchor=tk.NW,
                text=text,
                font=helv1,
                state=tk.DISABLED)
        self.game.board.tag_bind(self.rect, '<Button-1>', self.on_click)
        self.game.board.tag_bind(self.rect, '<Enter>', self.on_enter)
        self.game.board.tag_bind(self.rect, '<Leave>', self.on_leave)

        self.digitlist = []
        self.availablehints = set()
        for digit in range(10):
            div, mod = divmod(digit+2, 3)
            xt = xpixel + 9 + mod*8
            yt = ypixel + 5 + div*8

            digitid = self.game.board.create_text(xt, yt, text=digit,
                    font=helv2, state=tk.DISABLED, disabledfill=Colors.hints)
            self.digitlist.append(digitid)
            self.availablehints.add(digit)
        if self.ishead:
            self.togglehint((0,))

        self.bigone = self.game.board.create_text(
                xpixel + self.game.cellsize/2,
                ypixel + self.game.cellsize/2,
                text = '', font=helv3, state=tk.HIDDEN,
                disabledfill=Colors.hints)

    def __str__(self):
        return f'Cell at ({self.x}, {self.y})'

    @property
    def iserror(self):
        return self._iserror

    @iserror.setter
    def iserror(self, value):
        self._iserror = value
        self.updatecolor()

    @property
    def isselected(self):
        return self._isselected

    @isselected.setter
    def isselected(self, value):
        self._isselected = value
        self.updatecolor()

    @property
    def isrowselected(self):
        return self._isrowselected

    @isrowselected.setter
    def isrowselected(self, value):
        self._isrowselected = value
        self.updatecolor()

    @property
    def mouseover(self):
        return self._mouseover

    @mouseover.setter
    def mouseover(self, value):
        self._mouseover = value
        self.updatecolor()

    def updatecolor(self):
        if self.iserror:
            self.game.board.itemconfigure(self.rect, fill=Colors.error)
        elif self.isselected:
            self.game.board.itemconfigure(self.rect, fill=Colors.selected)
            self.game.selectionColoredCells.append(self)
        elif self.mouseover:
            self.game.board.itemconfigure(self.rect, fill=Colors.mouseover)
        elif self.isrowselected:
            self.game.board.itemconfigure(self.rect, fill=Colors.rowselected)
            self.game.selectionColoredCells.append(self)
        else:
            self.game.board.itemconfigure(self.rect, fill=Colors.foreground)

    def togglehint(self, numlist):
        if len(self.availablehints) == 1:
            (remaining,) = self.availablehints
            self.game.board.itemconfigure(self.digitlist[remaining], state=tk.DISABLED)
            self.game.board.itemconfigure(self.bigone, state=tk.HIDDEN)
        if len(self.availablehints) == 0:
            self.iserror = False

        for num in numlist:
            if num in self.availablehints:
                self.game.board.itemconfigure(self.digitlist[num], state=tk.HIDDEN)
                self.availablehints.remove(num)
            elif not (num == 0 and self.ishead):
                self.game.board.itemconfigure(self.digitlist[num], state=tk.DISABLED)
                self.availablehints.add(num)

        if len(self.availablehints) == 1:
            (remaining,) = self.availablehints
            self.game.board.itemconfigure(self.digitlist[remaining], state=tk.HIDDEN)
            self.game.board.itemconfigure(self.bigone, text=remaining, state=tk.DISABLED)
        elif len(self.availablehints) == 0:
            self.iserror = True

    def on_click(self, event=None):
        self.game.select(self)

    def on_enter(self, event=None):
        self.mouseover = True

    def on_leave(self, event=None):
        self.mouseover = False

    def on_arrowkey(self, key, state=0):
        if state == 1:
            self.togglehint(self.availablehints ^ {key})
        else:
            self.togglehint((key,))

class Clue:
    def __init__(self, game, cluetext, length, cell_list, clueref):
        self.game = game

        self._isselected = False
        self._ispassiveselected = False
        self._mouseover = False

        self.cluetext = self.__clean(cluetext)
        self.length = length
        self.cells = cell_list
        for cell in self.cells:
            cell.clues.append(self)
        self.clueref = clueref

        matchtext = '[0-9]+[AD]|[0-9,]+'
        self.cluestyle = tuple(re.split(matchtext, cluetext))
        self.refrences = tuple(re.findall(matchtext, cluetext))
        self.refrenceclues = tuple(ref for ref in self.refrences if ref[-1] in 'AD')
        self.game.cluetypes[self.cluestyle].append(cluetext)

        if self.clueref[1] == 'A':
            frame = self.game.across
        else:
            frame = self.game.down
        self.rowframes = frame.addclue(self.clueref[0], self.cluetext, self.length)
        self.updatecolor()

        for item in self.rowframes:
            item.bind('<Button-1>', self.on_click)

    def __str__(self):
        return f'{self.getname(self.clueref)}: {self.cluetext}'

    @property
    def isselected(self):
        return self._isselected

    @isselected.setter
    def isselected(self, value):
        self._isselected = value
        self.updatecolor()

    @property
    def ispassiveselected(self):
        return self._ispassiveselected

    @ispassiveselected.setter
    def ispassiveselected(self, value):
        self._ispassiveselected = value
        self.updatecolor()

    @property
    def mouseover(self):
        return self._mouseover

    @mouseover.setter
    def mouseover(self, value):
        self._mouseover = value
        self.updatecolor()

    def updatecolor(self):
        if self.isselected:
            color = Colors.selected
            self.game.selectionColoredClues.append(self)
        elif self.ispassiveselected:
            color = Colors.mouseover
            self.game.selectionColoredClues.append(self)
        elif self.mouseover:
            color = Colors.mouseover
        else:
            color = Colors.foreground
        for item in self.rowframes:
            item.configure(bg=color)

    def __clean(self, cluetext):
        output = ''
        for char in cluetext:
            if ord(char) < 65536:
                output += char
            else:
                if char not in self.game.charmapping:
                    self.game.charmapping[char] = f'[{len(self.game.charmapping) + 1}]'
                output += self.game.charmapping[char]
        return output

    def possibility_count_raw(self):
        prod = 1
        for cell in self.cells:
            prod *= len(cell.values)
        return prod

    def max(self):
        return int(''.join(str(max(cell.values)) for cell in self.cells))

    def min(self):
        return int(''.join(str(min(cell.values)) for cell in self.cells))

    def on_click(self, event=None):
        self.game.selectclue(self)

    @staticmethod
    def getref(cluename):
        return (int(cluename[:-1]), cluename[-1])

    @staticmethod
    def getname(clueref):
        return str(clueref[0]) + clueref[1]

    @staticmethod
    def dirswitch(direction):
        if direction == 'A':
            return 'D'
        elif direction == 'D':
            return 'A'
        else:
            print('Error: Direction not found')

class Game:
    def __init__(self, root, number=None):
        self.root = root

        self.cell_by_xy = {}
        self.xy_by_cluenum = {}
        self.cluenum_by_xy = {}
        self.maxx = 0
        self.maxy = 0

        myappid = u'crossnumber'
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

        self.cellsize = 35
        self.xoff = 5
        self.yoff = 5
        self.selectionColoredCells = []
        self.selectionColoredClues = []
        self.charmapping = {'𝑥': 'x', '𝟤': '^2', '𝟢': '0'}
        self.selectedCell = None
        self.directionbias = 'A'

        self.clues_by_clueref = {}
        self.cluetypes = collections.defaultdict(list)

        self.number = number
        self.root.title('Crossnumber')
        self.root.iconbitmap('noun_crossword puzzle_2699735.ico')

        def dummy():
            pass

        menubar = tk.Menu(self.root)

        filemenu = tk.Menu(menubar, tearoff=0)
        filemenu.add_command(label='Open', command=dummy)
        filemenu.add_command(label='Load', command=self.load)
        filemenu.add_command(label='Save', command=self.save)
        filemenu.add_command(label='Restart', command=self.restart)
        filemenu.add_separator()
        filemenu.add_command(label='Exit', command=self.root.quit)
        menubar.add_cascade(label='File', menu=filemenu)

        editmenu = tk.Menu(menubar, tearoff=0)
        editmenu.add_command(label='Undo', command=dummy)
        editmenu.add_command(label='Redo', command=dummy)
        editmenu.add_separator()
        editmenu.add_command(label='Start Fork', command=dummy)
        editmenu.add_command(label='Fail Fork', command=dummy)
        editmenu.add_command(label='Switch Fork', command=dummy)
        menubar.add_cascade(label='Edit', menu=editmenu)

        helpmenu = tk.Menu(menubar, tearoff=0)
        helpmenu.add_command(label='About', command=dummy)
        menubar.add_cascade(label='Help', menu=dummy)

        self.root.config(menu=menubar)

        self.board = tk.Canvas(self.root, width=600, height=600)
        self.board.grid(row=0, column=0, sticky=tk.NSEW)
        self.across = clueframe.ClueFrame(self.root, 'Across', width=300)
        self.across.grid(row=0, column=1, sticky=tk.NSEW)
        self.down = clueframe.ClueFrame(self.root, 'Down', width=300)
        self.down.grid(row=0, column=2, sticky=tk.NSEW)

        self.root.grid_columnconfigure(0, weight=1)
        #self.root.grid_columnconfigure(1, weight=1)
        #self.root.grid_columnconfigure(2, weight=1)
        #self.root.grid_rowconfigure(0, weight=1)

        self.root.bind('<KeyPress>', self.on_keydown)

        if number:
            self.open(number)

        rect = self.board.create_rectangle(
            self.xoff - 1,
            self.yoff - 1,
            self.xoff + (self.maxx+1)*self.cellsize + 1,
            self.yoff + (self.maxy+1)*self.cellsize + 1,
            fill=Colors.blanks)
        self.board.tag_lower(rect)

    def open(self, number):
        filename = f'crossnumber{number}.pdf'
        doc = fitz.open(filename)
        self.raw_clue_locations = self.__get_raw_clue_locations(doc)
        self.raw_clue_text = doc.getPageText(1)
        doc.close()

        self.__process_clue_locations()
        self.__process_clue_text()

    def __get_raw_clue_locations(self, doc):
        raw_clue_locations = []
        clue_check = 0
        for block in doc[0].getText('dict')['blocks']:
            if 'lines' not in block:
                continue
            for line in block['lines']:
                for span in line['spans']:
                    if span['flags'] == 4  and span['text'].isnumeric():
                        clue_check += 1
                        if str(clue_check) != span['text']:
                            print(f'Clue mismatch {span["text"]}.  Expecting {clue_check}.')
                            raise SyntaxError
                        raw_clue_locations.append((int(span['text']), span['bbox'][0], span['bbox'][1]))
        return raw_clue_locations

    def __get_increment_factor(self, distances, label):
        for increment in range(1, 50):
            total_offset = 0
            for x in distances:
                val = increment * (x - distances[0]) / (distances[-1] - distances[0])
                offset = abs(val - round(val))
                total_offset += offset
            if total_offset <= 1:
                return increment
        print('No {label} offset found')
        raise SyntaxError

    def __process_clue_locations(self):
        width = sorted(x[1] for x in self.raw_clue_locations)
        width_increment = self.__get_increment_factor(width, 'width')
        height = sorted(x[2] for x in self.raw_clue_locations)
        height_increment = self.__get_increment_factor(height, 'height')

        clue_locations = []
        for clue, w, h in self.raw_clue_locations:
            new_width = round(width_increment * (w - width[0]) / (width[-1] - width[0]))
            new_height = round(height_increment * (h - height[0]) / (height[-1] - height[0]))
            clue_locations.append((clue, new_width, new_height))
            self.start_clue_anchor(clue, new_width, new_height)
        return clue_locations

    def __process_clue_text(self):
        across_start = self.raw_clue_text.find('\nAcross\n')+1
        down_start = self.raw_clue_text.find('\nDown\n')+1

        across_clues = self.raw_clue_text[across_start:down_start]
        for x in re.findall('([0-9]+) (.*?)\(([0-9]+)\)', across_clues, re.DOTALL):
            self.create_clue(int(x[0]), 'A', x[1], int(x[2]))

        down_clues = self.raw_clue_text[down_start:]
        for x in re.findall('([0-9]+) (.*?)\(([0-9]+)\)', down_clues, re.DOTALL):
            self.create_clue(int(x[0]), 'D', x[1], int(x[2]))

    def create_clue(self, cluenum, direction, cluetext, length):
        cluetext = cluetext.replace('\n', ' ')
        while cluetext[-1] == ' ':
            cluetext = cluetext[:-1]
        if cluetext[-1] != '.':
            print('No period ending', cluetext)
        cell_list = self.create_clue_cells(cluenum, direction, int(length))
        clueref = (cluenum, direction)
        self.clues_by_clueref[clueref] = Clue(self, cluetext, int(length),
            cell_list, clueref)

    def display_basic(self):
        '''Prints an ascii output of the board'''
        for y in range(self.maxy + 1):
            print_val = []
            for x in range(self.maxx + 1):
                if (x, y) in self.cluenum_by_xy:
                    assert (x, y) in self.cell_by_xy
                    print_val.append(f'{self.cluenum_by_xy[(x,y)]:02}')
                elif (x, y) in self.cell_by_xy:
                    print_val.append('  ')
                else:
                    print_val.append('XX')
            print(' '.join(print_val))

    def save(self):
        savelist = []
        for cell in self.cell_by_xy.values():
            savelist.append((cell.x, cell.y, tuple(cell.availablehints)))
        with open(f'cross{self.number}.sav', 'w') as f:
            json.dump(savelist, f)

    def load(self):
        with open(f'cross{self.number}.sav') as f:
            jsondata = json.load(f)
        for x, y, availablehints in jsondata:
            cell = self.cell_by_xy[(x,y)]
            toggle = cell.availablehints ^ set(availablehints)
            cell.togglehint(toggle)

    def restart(self):
        for cell in self.cell_by_xy.values():
            toggle = cell.availablehints ^ set(range(10))
            cell.togglehint(toggle)

    def on_keydown(self, event):
        if 48 <= event.keycode <= 57:
            if self.selectedCell is not None:
                self.selectedCell.on_arrowkey(event.keycode-48, event.state)
        if event.keysym in ('Up', 'Down', 'Left', 'Right'):
            self.moveselected(event.keysym, event.state)

    def select(self, cellselection, toggle=True):
        '''Select cell for current input.
        Color selected and related cells'''
        self.clearselections()
        clues = cellselection.clues
        if len(clues) == 2:
            if toggle and cellselection is self.selectedCell:
                self.directionbias = Clue.dirswitch(self.directionbias)
            if self.directionbias == 'A':
                clueselection = clues[0]
                clues[1].ispassiveselected = True
            else:
                clueselection = clues[1]
                clues[0].ispassiveselected = True
        else:
            clueselection = clues[0]
            self.directionbias = clueselection.clueref[1]
        clueselection.isselected = True
        for cell in clueselection.cells:
            if cell is not cellselection:
                cell.isrowselected = True
        cellselection.isselected = True
        self.selectedCell = cellselection

    def selectclue(self, clue):
        '''Select cell based on clue click'''
        self.directionbias = clue.clueref[1]
        if self.selectedCell in clue.cells:
            self.select(self.selectedCell, toggle=False)
        else:
            self.select(clue.cells[0], toggle=False)

    def clearselections(self):
        '''Clears cell/clue colors caused bycurrent selections'''
        while self.selectionColoredCells:
            cell = self.selectionColoredCells.pop()
            cell.isselected = False
            cell.isrowselected = False
        while self.selectionColoredClues:
            clue = self.selectionColoredClues.pop()
            clue.isselected = False
            clue.ispassiveselected = False

    def start_clue_anchor(self, cluenum, x, y):
        self.cell_by_xy[(x, y)] = Cell(self, True, x, y, text=cluenum)
        self.xy_by_cluenum[cluenum] = (x, y)
        self.cluenum_by_xy[(x, y)] = cluenum
        self.maxx = max(x, self.maxx)
        self.maxy = max(y, self.maxy)

    def create_clue_cells(self, cluenum, direction, length):
        x, y = self.xy_by_cluenum[cluenum]
        cell_list = []
        for i in range(int(length)):
            if direction == 'A':
                ref = (x+i, y)
            else:
                ref = (x, y+i)
            if ref not in self.cell_by_xy:
                self.cell_by_xy[ref] = Cell(self, False, ref[0], ref[1])
            cell_list.append(self.cell_by_xy[ref])
        return cell_list

    def moveselected(self, direction, state):
        if self.selectedCell is None:
            return
        x = self.selectedCell.x
        y = self.selectedCell.y
        xshift, yshift = {'Up': (0, -1), 'Down': (0, 1), 'Left': (-1, 0), 'Right': (1, 0)}[direction]
        if state & 1:
            count = 1
            while (x + xshift*count,y + yshift*count) in self.cell_by_xy:
                count += 1
            if count >= 2:
                self.cell_by_xy[(
                    x + xshift*(count-1),
                    y + yshift*(count-1))].on_click()
        else:
            if (x + xshift, y + yshift) in self.cell_by_xy:
                self.cell_by_xy[(x + xshift, y + yshift)].on_click()

if __name__ == '__main__':
    root = tk.Tk()
    cross = Game(root, 10)
    root.mainloop()


# print(cross.display_basic())

# for x, y in sorted(cross.cluetypes.items(), key=lambda x:-len(x[1])):
#     print(x, len(y))
#     for i in y:
#         print('     ', i)

# cross.clues.keys()

# cross.clues[(1, 'A')].possibility_raw()

# width = [5, 6]

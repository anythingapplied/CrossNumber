import re
import fitz
import collections
import tkinter as tk
import tkinter.font

class Cell:
    def __init__(self, minimum, x, y):
        self.values = list(range(minimum, 10))
        self.x = x
        self.y = y

    def setrect(self, rect):
        self.rect = rect

class Grid:
    def __init__(self):
        self.cell_by_xy = {}
        self.xy_by_cluenum = {}
        #self.clue_cells = {}
        self.cluenum_by_xy = {}
        self.maxx = 0
        self.maxy = 0

    def start_clue_anchor(self, cluenum, x, y):
        self.cell_by_xy[(x, y)] = Cell(1, x, y)
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
                self.cell_by_xy[ref] = Cell(0, x, y)
            cell_list.append(self.cell_by_xy[ref])
        return cell_list

class Clue:
    def __init__(self, cross, cluetext, length, cell_list):
        self.cross = cross
        self.cluetext = cluetext
        self.length = length
        self.cells = cell_list

        matchtext = "[0-9]+[AD]|[0-9,]+"
        self.cluestyle = tuple(re.split(matchtext, cluetext))
        self.refrences = re.findall(matchtext, cluetext)
        self.cross.cluetypes[self.cluestyle].append(cluetext)

    def possibility_count_raw(self):
        prod = 1
        for cell in self.cells:
            prod *= len(cell.values)
        return prod

    def max(self):
        return int("".join(str(max(cell.values)) for cell in self.cells))

    def min(self):
        return int("".join(str(min(cell.values)) for cell in self.cells))

    @staticmethod
    def getref(cluename):
        return (int(cluename[:-1]), cluename[-1])

    @staticmethod
    def getname(clueref):
        return str(clueref[0]) + clueref[1]

class CrossNumber:
    def __init__(self, number):
        self.grid = Grid()
        self.clues = {}
        self.cluetypes = collections.defaultdict(list)

        filename = f"crossnumber{number}.pdf"
        doc = fitz.open(filename)
        self.raw_clue_locations = self.__get_raw_clue_locations(doc)
        self.raw_clue_text = doc.getPageText(1)
        doc.close()

        self.__process_clue_locations(self.raw_clue_locations)
        self.__process_clue_text(self.raw_clue_text)

    def __get_raw_clue_locations(self, doc):
        raw_clue_locations = []
        clue_check = 0
        for block in doc[0].getText("dict")['blocks']:
            if 'lines' not in block:
                continue
            for line in block['lines']:
                for span in line['spans']:
                    if span['flags'] == 4  and span['text'].isnumeric():
                        clue_check += 1
                        if str(clue_check) != span['text']:
                            t = f"Clue mismatch {span['text']}.  Expecting {clue_check}."
                            print(t)
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
        print("No {label} offset found")
        raise SyntaxError

    def __process_clue_locations(self, raw_clue_locations):
        width = sorted(x[1] for x in raw_clue_locations)
        width_increment = self.__get_increment_factor(width, "width")
        height = sorted(x[2] for x in raw_clue_locations)
        height_increment = self.__get_increment_factor(height, "height")

        clue_locations = []
        for clue, w, h in raw_clue_locations:
            new_width = round(width_increment * (w - width[0]) / (width[-1] - width[0]))
            new_height = round(height_increment * (h - height[0]) / (height[-1] - height[0]))
            clue_locations.append((clue, new_width, new_height))
            self.grid.start_clue_anchor(clue, new_width, new_height)
        return clue_locations

    def __process_clue_text(self, raw_clue_text):
        across_start = self.raw_clue_text.find("\nAcross\n")+1
        down_start = self.raw_clue_text.find("\nDown\n")+1

        across_clues = self.raw_clue_text[across_start:down_start]
        for x in re.findall("([0-9]+) (.*?)\(([0-9]+)\)", across_clues, re.DOTALL):
            self.create_clue(int(x[0]), 'A', x[1], int(x[2]))

        down_clues = self.raw_clue_text[down_start:]
        for x in re.findall("([0-9]+) (.*?)\(([0-9]+)\)", down_clues, re.DOTALL):
            self.create_clue(int(x[0]), 'D', x[1], int(x[2]))

    def create_clue(self, cluenum, direction, cluetext, length):
        cluetext = cluetext.replace("\n", " ")
        while cluetext[-1] == " ":
            cluetext = cluetext[:-1]
        if cluetext[-1] != ".":
            print("No period ending", cluetext)
        cell_list = self.grid.create_clue_cells(cluenum, direction, int(length))
        self.clues[(cluenum, direction)] = Clue(self, cluetext, int(length), cell_list)

    def display_basic(self):
        """Prints an ascii output of the board"""
        for y in range(self.grid.maxy + 1):
            print_val = []
            for x in range(self.grid.maxx + 1):
                if (x, y) in self.grid.cluenum_by_xy:
                    assert (x, y) in self.grid.cell_by_xy
                    print_val.append(f'{self.grid.cluenum_by_xy[(x,y)]:02}')
                elif (x, y) in self.grid.cell_by_xy:
                    print_val.append("  ")
                else:
                    print_val.append("XX")
            print(" ".join(print_val))

    def run(self):
        self.window = tk.Tk()

        helv = tk.font.Font(self.window, family='Helvetica', size=7)

        self.window.title("Crossnumber")
        board = tk.Canvas(self.window, width=600, height=600)

        board.grid(row=0, column=0)
        size = 35
        xoff = 5
        yoff = 5

        def click(x, y):
            def clickaction(event):
                pass
            return clickaction

        for y in range(self.grid.maxy + 1):
            for x in range(self.grid.maxx + 1):
                if (x, y) in self.grid.cluenum_by_xy:
                    rect = board.create_rectangle(
                        xoff + x*size,
                        yoff + y*size,
                        xoff + (x+1)*size,
                        yoff + (y+1)*size)
                    self.grid.cell_by_xy[(x, y)].setrect(rect)
                    board.create_text(
                        xoff + x*size + 1,
                        yoff + y*size - 1,
                        anchor=tk.NW,
                        text=self.grid.cluenum_by_xy[(x, y)],
                        font=helv
                    )
                    board.tag_bind(rect, '<Button-1>', click(x, y))
                elif (x, y) in self.grid.cell_by_xy:
                    rect = board.create_rectangle(
                        xoff + x*size,
                        yoff + y*size,
                        xoff + (x+1)*size,
                        yoff + (y+1)*size)
                    self.grid.cell_by_xy[(x, y)].setrect(rect)
                    board.tag_bind(rect, '<Button-1>', click(x, y))
                else:
                    rect = board.create_rectangle(
                        xoff + x*size,
                        yoff + y*size,
                        xoff + (x+1)*size,
                        yoff + (y+1)*size,
                        fill="black")

        across = tk.Canvas(self.window, width=300, height=400)
        across.grid(row=0, column=1)

        down = tk.Canvas(self.window, width=300, height=400)
        down.grid(row=0, column=2)

        self.window.mainloop()

cross = CrossNumber(10)
cross.run()

# print(cross.display_basic())

# for x, y in sorted(cross.cluetypes.items(), key=lambda x:-len(x[1])):
#     print(x, len(y))
#     for i in y:
#         print("     ", i)

# cross.clues.keys()

# cross.clues[(1, 'A')].possibility_raw()

# width = [5, 6]

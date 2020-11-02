import tkinter as tk

class ClueFrame(tk.Frame):
    def __init__(self, parent, title, *arg, **karg):
        super().__init__(parent, *arg, **karg)
        self.canvas = tk.Canvas(self, *arg, **karg)
        self.frame = tk.Frame(self.canvas, *arg, **karg)
        self.vsb = tk.Scrollbar(self, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)

        self.vsb.pack(side='right', fill='y')
        self.canvas.pack(side='left', fill='both', expand=True)
        self.canvas.create_window((0, 0), window=self.frame, anchor=tk.NW,
                width=300, tags='self.frame')

        #self.canvas.bind('<Configure>', self.onCanvasConfigure)
        self.frame.bind('<Configure>', self.onFrameConfigure)
        self.row = 1
        titlebar = tk.Label(self.frame, text=title)
        titlebar.grid(row=0, column=0, columnspan=3)
        #self.frame.grid_columnconfigure(0, weight=0)
        self.frame.grid_columnconfigure(1, weight=1)
        #self.frame.grid_columnconfigure(2, weight=0)
        #self.grid_rowconfigure(0, weight=1)
        self.canvas.grid_rowconfigure(0, weight=1)
        self.rows = []

    def addclue(self, cluenum, cluetext, cluelength):
        label1 = tk.Label(self.frame, text=cluenum, width=2, anchor=tk.NE)
        label1.grid(row=self.row, column=0, sticky=tk.NSEW)

        label2 = tk.Label(self.frame, text=cluetext, width=34, wraplength=200,
                anchor=tk.NW, justify=tk.LEFT)
        label2.grid(row=self.row, column=1, sticky=tk.NSEW)

        label3 = tk.Label(self.frame, text=cluelength, width=2, anchor=tk.NE)
        label3.grid(row=self.row, column=2, sticky=tk.NSEW)
        self.rows.append((label1, label2, label3))
        self.row += 1
        return self.rows[-1]

    def onFrameConfigure(self, event):
        '''Reset the scroll region to encompass the inner frame'''
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))

    # def onCanvasConfigure(self, event):
    #     print('canvas event', event.width)
    #     print('frame width before', self.frame.winfo_width())
    #     self.frame.configure(width=event.width)
    #     print('frame width after', self.frame.winfo_width())

if __name__ == '__main__':
    root=tk.Tk()
    across = ClueFrame(root, 'Across')
    root.grid_columnconfigure(0, weight=8)
    root.grid_columnconfigure(1, weight=8)
    root.grid_columnconfigure(2, weight=2)
    for x in range(20):
        across.addclue(x, 'hello ' * (x//3 + 1), 15)
    across.grid(row=0, column=1)
    down = ClueFrame(root, 'Down')
    for x in range(20):
        down.addclue(x, 'down', 15)
    down.grid(row=0, column=2)
    root.mainloop()

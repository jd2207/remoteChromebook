""" Module for CellNet classes """

import cell
from pubsub import pub


class CellNet(object):
  """ An abstract collection of Cells 
      The collection of Cells may be ticked() - i.e. modified en-masse according to the re-generation rules of each cell
      to form a next generation  
  Usage example: See simpleCellTriangle 
  """

  def __init__(self):
    """ Usually overridden by subclasses. Otherwise, makes a new CellNet which is just a list of Cells """ 
    self.cells = getattr(self, 'cells', [])  # set self.cells to [] if not defined by the subclass __init__() 
    self.generation = 0 
    self.setupNeighbors()
     
  def makeCell(self, identity ):
    """ Make a cell for this class of CellNet - overridden by child classes""" 
    return cell.BaseCell( identity )
  
  def setupNeighbors(self):
    """ Create the links between Cell neighbors - overridden by child classes""" 
    pass
  
  def toList(self):
    """ convert the CellNet to one dimensional list of the constituent cells -  overridden by child classes""" 
    return self.cells
    
  def fromList(self, cells):
    """ convert a list of Cells to create a new CellNet of this class -  overridden by child classes""" 
    return cells
  
  def tick(self, generations=1):
    """ regenerate the Cells of the entire grid and update viewers """                             
    while generations > 0:
      cellList = self.toList()                            # Convert the grid to a one dimensional list
      newList = [ cell.nextGen() for cell in cellList ]   # Create a list of cells based on old one


      for cell in newList:                                # the neighbors of every new cell need to be the descendants of old neighbors
        cell.neighbors = [ n.descendant for n in cell.neighbors ]
    
      self.cells = self.fromList(newList)               # Convert it back to a grid and overwrite the original list
      self.generation += 1; generations -= 1
      pub.sendMessage('CellNet-Ticked')
  
  def dump(self):
    cellList = self.toList()
    return 'Gen %i:\n' % self.generation + \
           "%s\n"*len(cellList) % tuple ([ str(cell) for cell in cellList ])



class simpleCellTriangle(CellNet):
  """ a triangle of three Cells
      - which are mutual neighbors
      - which are IntegerCells 
          - state is an integer
          - next generation cell has a state which is the sum of the current neighbor cells sate 
  Usage:
  import Cell
  cn = Cell.simpleCellTriangle([ Cell.IntegerCell('Cell A', 1), 
                                 Cell.IntegerCell('Cell B', 5), 
                                 Cell.IntegerCell('Cell C', 7) ])
  [cell.state for cell in cn.cells]
  [1, 5, 7]
  cn.tick()
  [cell.state for cell in cn.cells]
  [12, 8, 6]
  
  """
  def __init__(self, listOfCells):
    self.cells = listOfCells
    super(simpleCellTriangle, self).__init__()
  
  def setupNeighbors(self):
    self.cells[0].neighbors = [ self.cells[1], self.cells[2] ]
    self.cells[1].neighbors = [ self.cells[0], self.cells[2] ]
    self.cells[2].neighbors = [ self.cells[0], self.cells[1] ]

  def __str__(self):
    return str( [ self.cells[0].state, self.cells[1].state, self.cells[2].state ]  ) 



class CellGrid(CellNet):
  """ A CellNet with a specific arrangement of Cells where:
      - cells are contained in a 2-D array (rows, columns)
      - the neighbors of each cell are those which are immediately adjacent (i.e the 8 cells of the compass points for non-edge, non-corner cells) 
  """  
  def __init__(self, rows=10, cols=10):     
    self.rows = rows
    self.cols = cols
    self.cells = [ [ self.makeCell( (row,col) ) for col in range(self.cols) ] for row in range(self.rows) ]
    super(CellGrid, self).__init__()
        
  def setupNeighbors(self):
    for row in range(self.rows):
      for col in range(self.cols):
        nw = (row-1, col-1) if (row>0 and col>0) else None      # vars named after compass points
        n = (row-1, col) if (row>0) else None
        ne = (row-1, col+1) if (row>0 and col<self.cols-1) else None
        e = (row, col+1) if (col<self.cols-1) else None
        se = (row+1, col+1) if (row<self.rows-1 and col<self.cols-1) else None
        s = (row+1, col) if (row<self.rows-1) else None
        sw = (row+1, col-1) if (row<self.rows-1 and col>0) else None
        w = (row, col-1) if (col>0) else None
    
        self.cells[row][col].neighbors = [ self.cells[ ncell[0] ][ ncell[1] ] for ncell in (n, ne, e, se, s, sw, w, nw) if ncell ]
  
  def fromList(self, cells):
    """ Create a 2D array of cells from a list of cells (same rows, cols as this instance) """  
    cells.reverse()
    newCells  = [ [ cells.pop() for col in range(self.cols) ] for row in range(self.rows) ]
    return newCells 

  def toList(self):
    """ returns a 1 dimensional list of the cells of the grid """
    return [ self.cells[row][col] for row in range(self.rows) for col in range(self.cols) ]



class BooleanCellGrid(CellGrid):
  """ Specialist CellGrid consisting of BooleanCells """

  def makeCell(self, rowColTupleIdentity ):
    return cell.BooleanCell( rowColTupleIdentity )

  
# ==================================================================================================
# Grid Viewer Controllers 
# ==================================================================================================
  
class CellGrid_VC(object):
  """ Generic viewer/controller for CellGrid objects 
  
  Usage:  see example of BooleanGridViewerController class
  
  """
  
  def __init__ (self, cellGrid):
    self.cellGrid = cellGrid
    self.setViewers()
    pub.subscribe(self.refreshOnTick, 'CellNet-Ticked')   # register to listen for tick() events, and bind to refreshOnTick() 
    
  def setViewers(self):
    """ Overridden by subclasses - creates a list of CellViewerController objects for the grid"""
    self.viewers = [ [ cell.Cell_VC(c) for c in row ] for row in self.cellGrid.cells ]
    
  def mutateCell(self, row, col):
    cell = self.cellGrid.cells[row][col]
    cell.mutate()
    self.viewers[row][col].refresh()    
    
  def updateCell(self, row, col, **kwargs):
    cell = self.cellGrid.cells[row][col]
    cell.update(**kwargs)
    self.viewers[row][col].refresh()    
  
  def play(self, generations=1):
    """ tick() the underlying grid object a given number of times """
    self.cellGrid.tick(generations)
    
  def refreshOnTick(self):
    """ recreate the viewers """
    for vrow in self.viewers:
      for v in vrow:
          v.setCell(v.cell.descendant)
    
  def refresh(self):
    """ Overridden by subclasses """
    pass
    
  def __str__(self):
    """ Display a textual view of the grid state"""
    cols = self.cellGrid.cols
    s =  '---' * (cols + 1) + '\n' 
    s += '   ' +  (' %i ' * cols) % tuple(range(cols)) + '\n'
    i = 0
    for row in self.viewers:
      s += ' %i ' % i
      for viewer in row:
        s += ' ' + str(viewer) + ' ' 
      s += '\n'
      i += 1
    s += '---' * (cols + 1)
    return s


class BooleanGrid_VC(CellGrid_VC):
  """ Generic viewer/controller for BooleanCellGrid objects 
  
  Usage: 
  >>> import Cell, CellViewerController
  >>> g = Cell.BooleanCellGrid(3,3)
  >>> vc = CellViewerController.BooleanGridViewerController(g)
  >>> vc.modifyCell(0,1,state=1)
  >>> vc.modifyCell(1,1,state=1)
  >>> vc.modifyCell(2,1,state=1)
  
  >>> print vc
------------
    0  1  2
 0  -  *  -
 1  -  *  -
 2  -  *  -
------------
  >>> vc.tick()
  >>> print vc
------------
    0  1  2
 0  *  -  *
 1  *  -  *
 2  *  -  *
------------
  """
    
  def setViewers(self):
    """ Overridden by subclasses - creates a list of CellViewerController objects for the grid"""
    self.viewers = [ [ cell.BooleanCell_VC(c) for c in row ] for row in self.cellGrid.cells ]

  
if __name__ == '__main__':
  print "For tests use module 'testCellNet'"
import sys
# import math
import time
import Queue

time_t = time.time()

# Optimizations
# Read this somewhere...python executes some periodic checks to sync across threads
# and that for single-thread programs, a high number setting to not check so often
# may improve performance.
# Since it's only 1 line, and it's already python...might as well :P
sys.setcheckinterval(1000000)

# Behaviors
STOP_SHORT_BARRELS = True
STACK_OVERFLOW = 255
BFS_SEARCH_DEPTH = 3

# Const
MINE = 3
BARREL = 4
CANNONBALL = 2
ENSHIP = -1
MYSHIP = 1
OCCSHIP = 5

SHIP_SEEK_TARGET_COOLDOWN = 2
SHIP_STUCK_COOLDOWN = 5

TMP_IDs = 10000

OFFSET_ADJCELL = 2
DELAY_CANNONBALL = 3
DELAY_FIRE = 2
DELAY_MINE = 4

# Scoring

# Traversals
hexOdd = [(1, 0), (1, -1), (0, -1), (-1, 0), (0, 1), (1, 1)]
hexEven = [(1, 0), (0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1)]
hexAdj = [hexEven, hexOdd]
precomp_distTo = [[None for i in xrange(21)] for j in xrange(23)]
precomp_adjCell = [[[[None for a in xrange(2)] for o in xrange(6)] for y in xrange(25)] for x in xrange(27)]

# Helper functions
def verifyLoc(loc):
    x = loc[0]
    y = loc[1]
    return (x < 23 and x > -1 and y < 21 and y > -1)

def distTo(x1, y1, x2, y2):
    xp1 = x1 - (y1 - (y1 & 1)) / 2
    zp1 = y1
    yp1 = -(xp1 + zp1)
    xp2 = x2 - (y2 - (y2 & 1)) / 2
    zp2 = y2
    yp2 = -(xp2 + zp2)
    return (abs(xp1 - xp2) + abs(yp1 - yp2) + abs(zp1 - zp2)) / 2

def locToKey(loc):
    return loc[0]*100+loc[1]

def keyToLoc(key):
    return (int(key/100), key%100)

def cellAhead(loc, orien):
    tmp_bow = (loc[0]+hexAdj[loc[1]%2][orien][0], loc[1]+hexAdj[loc[1]%2][orien][1])
    return tmp_bow

def cellBehind(loc, orien):
    tmp_stern = (loc[0]+hexAdj[loc[1]%2][(orien-3)%6][0], loc[1]+hexAdj[loc[1]%2][(orien-3)%6][1])
    return tmp_stern

def shipSpace(x, y, orien):
    tmp_mid = (x, y)
    tmp_bow = precomp_adjCell[x+OFFSET_ADJCELL][y+OFFSET_ADJCELL][orien][0]
    tmp_stern = precomp_adjCell[x+OFFSET_ADJCELL][y+OFFSET_ADJCELL][orien][1]
    return (tmp_bow, tmp_mid, tmp_stern)

def radiusList(x, y, radius, filter):
    lower_x = x-radius
    upper_x = x+radius
    li = []
    if (filter):
        for i in xrange(lower_x, upper_x+1):
            if (verifyLoc((i, y))):
                li.append((i, y))
        for i in xrange(1, radius):
            cur_lower_x = lower_x
            cur_upper_x = upper_x
            cur_y = y-i
            if (cur_y%2==0):
                cur_lower_x += 1
            else:
                cur_upper_x -= 1
            for j in xrange(cur_lower_x, cur_upper_x+1):
                if (verifyLoc((j, cur_y))):
                    li.append((j, cur_y))
                if (verifyLoc((j, y+i))):
                    li.append((j, y+i))
    else:
        for i in xrange(lower_x, upper_x+1):
            li.append((i, y))
        for i in xrange(1, radius):
            cur_lower_x = lower_x
            cur_upper_x = upper_x
            cur_y = y-i
            if (cur_y%2==0):
                cur_lower_x += 1
            else:
                cur_upper_x -= 1
            for j in xrange(cur_lower_x, cur_upper_x+1):
                li.append((j, cur_y))
                li.append((j, y+i))
    return li

def getSurroundingCells(curPosition, end_orien):
    global_precompCells = precomp_adjCell
    global_offset = OFFSET_ADJCELL
    end_bow = curPosition[0]
    end_mid = curPosition[1]
    end_stern = curPosition[2]
    surroundingCells = []
    for i in xrange(6): # Excluding already occupied cells
        if (i == end_orien or i == (end_orien-3)%6):
            continue
        curAhead = global_precompCells[end_mid[0]+global_offset][end_mid[1]+global_offset][i][0]
        surroundingCells.append(curAhead)
    end_ahead_bow = global_precompCells[end_bow[0]+global_offset][end_bow[1]+global_offset][end_orien][0]
    surroundingCells.append(end_ahead_bow)
    surroundingCells.append(end_ahead_bow)
    surroundingCells.append(global_precompCells[end_bow[0]+global_offset][end_bow[1]+global_offset][end_orien][0])
    surroundingCells.append(global_precompCells[end_bow[0]+global_offset][end_bow[1]+global_offset][end_orien][0])
    cur_port = global_precompCells[end_mid[0]+global_offset][end_mid[1]+global_offset][(end_orien+1)%6][0]
    cur_port = global_precompCells[end_mid[0]+global_offset][end_mid[1]+global_offset][(end_orien-1)%6][0]
    surroundingCells.append(global_precompCells[cur_port[0]+global_offset][cur_port[1]+global_offset][(end_orien+1)%6][0]) # Port ahead
    surroundingCells.append(global_precompCells[cur_port[0]+global_offset][cur_port[1]+global_offset][(end_orien-1)%6][0]) # Starboard ahead
    return surroundingCells

def adjacentShipCells(loc, orien):
    global_precompCells = precomp_adjCell
    global_offset = OFFSET_ADJCELL
    bow = global_precompCells[loc[0]+global_offset][loc[1]+global_offset][orien][0]
    stern = global_precompCells[loc[0]+global_offset][loc[1]+global_offset][orien][1]
    adjCells = []

    adjCells.append(global_precompCells[loc[0]+global_offset][loc[1]+global_offset][(orien+1)%6][0])
    adjCells.append(global_precompCells[loc[0]+global_offset][loc[1]+global_offset][(orien-1)%6][0])
    adjCells.append(global_precompCells[loc[0]+global_offset][loc[1]+global_offset][(orien+1)%6][1])
    adjCells.append(global_precompCells[loc[0]+global_offset][loc[1]+global_offset][(orien-1)%6][1])
    for cur_orien in [orien, (orien+1)%6, (orien-1)%6]:
        adjCells.append(global_precompCells[bow[0]+global_offset][bow[1]+global_offset][cur_orien][0])
        adjCells.append(global_precompCells[stern[0]+global_offset][stern[1]+global_offset][cur_orien][0])

    adjKeyList = [locToKey(cell) for cell in adjCells]

    return (adjCells, adjKeyList)

# Move Simulation function
    # Takes in the state of the ship, obstacles on the map and the action we're simulating
    # v_list here keeps track of where we've visited, as in my simulation, I do not interact with game objects
    # unless it affects the movement (so only edges/other ships).
#RETURNS: (x, y, speed, orien, v_list)
def verifyMove(loc, speed, orien, action, occ_list):
    orig_x = loc[0]
    orig_y = loc[1]
    orig_orien = orien
    orig_speed = speed
    orig_spaces = shipSpace(orig_x, orig_y, orig_orien)
    orig_keys = [locToKey(space) for space in orig_spaces]
    cur_x = orig_x
    cur_y = orig_y
    cur_speed = orig_speed + action.transformation[0]
    if (cur_speed > 2 or cur_speed < 0): # Filter out impossible speeds
        return None
    # Visited List
    v_list = []

    # Move Ship forward
    if (cur_speed > 0):
        cur_bow = orig_spaces[0]
        cur_ahead_bow = precomp_adjCell[cur_bow[0]+OFFSET_ADJCELL][cur_bow[1]+OFFSET_ADJCELL][orig_orien][0]
        for i in xrange(cur_speed):
            if (locToKey(cur_ahead_bow) in occ_list):
                cur_speed = 0
                if (isinstance(action, Faster) and orig_speed == 0):
                    return None
                break
            if (not verifyLoc(cur_bow)):
                cur_speed = 0
                if (isinstance(action, Faster) and orig_speed == 0):
                    return None
                break
            cur_key = locToKey(cur_ahead_bow)
            cur_x = cur_bow[0]
            cur_y = cur_bow[1]
            cur_bow = cur_ahead_bow
            cur_ahead_bow = precomp_adjCell[cur_bow[0]+OFFSET_ADJCELL][cur_bow[1]+OFFSET_ADJCELL][orig_orien][0]
            if (cur_key not in v_list and cur_key not in orig_keys):
                v_list.append(cur_key)

    # Rotation
    cur_orien = (orig_orien + action.transformation[1])%6
    cur_spaces = shipSpace(cur_x, cur_y, cur_orien)
    for space in cur_spaces:
        cur_key = locToKey(space)
        if (cur_key not in v_list and cur_key not in orig_keys):
            v_list.append(cur_key)
    if (cur_orien == orig_orien):
        return (cur_x, cur_y, cur_speed, cur_orien, v_list)

    # Apply rotation
    cur_bow_key = locToKey(cur_spaces[0])
    cur_stern_key = locToKey(cur_spaces[2])
    if (cur_bow_key in occ_list or cur_stern_key in occ_list):
        return None
    if (cur_bow_key not in v_list and cur_key not in orig_keys):
        v_list.append(cur_bow_key)
    if (cur_stern_key not in v_list and cur_key not in orig_keys):
        v_list.append(cur_stern_key)
    return (cur_x, cur_y, cur_speed, cur_orien, v_list)

#TODO: BFS Actual
# Since the BFS forms the backbone of the algo...I leave it up to you to learn and implement it here :P
# I will however, provide a pseudo code to guide you through...
def bfs():
    q = Queue.Queue()
    # Push initial states into queue
    while (not q.empty()):
        #1. Simulate current move
        #2. Check for validity
        #3. Score move
            # Accumulative scoring for certain factors?
            # Score position only when sufficient depth has been reached?
        #4. Propagate from one state -> the next
            # Some pruning can be done here
            # E.g.  if (end_speed < 2):
            #           q.put(FASTER)
    # Return best-scoring move
    return None

# Some standard classes to store data in a more readable fashion
class Command(object):

    def __init__(self):
        self.transformation = None

class Port(Command):

    def __init__(self):
        self.transformation = (0, 1)

    def printCmd(self):
        return "PORT"

class Starboard(Command):

    def __init__(self):
        self.transformation = (0, -1)

    def printCmd(self):
        return "STARBOARD"

class Faster(Command):

    def __init__(self):
        self.transformation = (1, 0)

    def printCmd(self):
        return "FASTER"

class Slower(Command):

    def __init__(self):
        self.transformation = (-1, 0)

    def printCmd(self):
        return "SLOWER"

class Wait(Command):

    def __init__(self):
        self.transformation = (0, 0)

    def printCmd(self):
        return "WAIT"

class MineCMD(Wait):

    def __init__(self, x, y):
        super(MineCMD, self).__init__()
        self.x = x
        self.y = y

    def actionLoc(self):
        return (self.x, self.y)

    def printCmd(self):
        return "MINE"

class Fire(Wait):

    def __init__(self, x, y):
        super(Fire, self).__init__()
        self.x = x
        self.y = y

    def actionLoc(self):
        return (self.x, self.y)

    def printCmd(self):
        return "FIRE {} {}".format(self.x, self.y)

class Barrel(object):

    def __init__(self, ID, rum, x, y):
        self.ID = ID
        self.rum = rum
        self.x = x
        self.y = y
        self.alive = False

    def tick(self):
        if (not self.alive):
            del barrels[self.ID]

class Mine(object):

    def __init__(self, ID, x, y):
        self.ID = ID
        self.x = x
        self.y = y
        self.alive = False

    def tick(self):
        if (not self.alive):
            del mines[self.ID]

class Cannonball(object):

    def __init__(self, ID, originID, ttt, x, y):
        self.ID = ID
        self.originID = originID
        self.ttt = ttt
        self.x = x
        self.y = y
        self.alive = False
        self.refGrid = cannonGrid[self.x][self.y]

    def tick(self):
        self.ttt -= 1
        if (self.ttt < 1 or not self.alive):
            del cannonballs[self.ID]
            del self.refGrid[self.ID]

class Ship(object):

    def __init__(self, ID, orientation, speed, rum, team, x, y):
        self.ID = ID
        self.orientation = orientation
        self.speed = speed
        self.rum = rum
        self.team = team
        self.x = x
        self.y = y
        self.canFire = 0
        self.canMine = 0
        self.alive = False
        self.tgtCD = 0
        self.curTgt = (11, 10)
        self.prevX = x
        self.prevY = y
        self.stuck = False
        self.stuckConut = 0
        self.curMove = Wait()
        self.curTargetedBarrel = None
        self.sacrifice = False
        self.lamb_target = None
        self.projected_vList = []
        self.scored_projection = []
        self.projected_mineKeys = []
        self.closestBarrelKey = -1

    def update(self, orientation, speed, rum, x, y):
        self.orientation = orientation
        self.speed = speed
        self.rum = rum
        self.x = x
        self.y = y

    def tick(self):
        self.lamb_target = None
        self.sacrifice = False
        self.closestBarrelKey = -1
        if (not self.alive):
            del ships[self.ID]
        else:
            self.canFire -= 1 if self.canFire > 0 else 0
            self.canMine -= 1 if self.canMine > 0 else 0
            self.tgtCD -= 1 if self.tgtCD > 0 else 0

    def project(self, numTurns):
        # Runs another implementation of BFS algo
        #TODO: BFS
        # We want to find out the following (to be used later):
        self.scored_projection = []         # List of visited cells, scored for probability of occupying said cell
        self.projected_vDict = dict()       # Range of ship with its corresponding minimal depth required to visit cell
        self.projected_mineKeys = []        # Predicted locations ship can MINE at
        self.closestBarrelKey = -1          # Closest barrel to the ship

    def predictFires(self):
        # What we want to do is to simulate enemy fires upon self
        # Really close to enemy ==> Enemy fires directly on ship's center
        # Not that good of an idea to simulate beyond time 2 for cannonball to land
        # That would restrict your pathing too pessimistically
        # Use previously computed projected location information to evaluate where enemy is likely to shoot
        # Add such predicted fires into the global arrays for our BFS eval function to access
        return None

    def offer(self, tgtShip): # Sacrifice self as offering for other ship
        self.curMove = Wait()
        init_t = time.time()
        # We project forward our targeted ship slightly to anticipate reaching and self-destruct in front of it
        tgtResult = verifyMove((tgtShip.x, tgtShip.y), tgtShip.speed, tgtShip.orientation, tgtShip.curMove, [])
        tgtResult = verifyMove((tgtResult[0], tgtResult[1]), tgtResult[2], tgtResult[3], Wait(), [])
        moveLoc = (tgtResult[0], tgtResult[1])
        sacrifice_move = None

        # Precompute occupancy
        mine_key_list = [locToKey((mine.x, mine.y)) for mine in mines.values()]
        shipsInfo = []
        occ_list = []
        en_v_list = []
        my_v_list = []
        my_ship_end_info = []
        for ship in ships.values():
            if (ship.ID == self.ID):
                continue
            updated_info = verifyMove((ship.x, ship.y), ship.speed, ship.orientation, ship.curMove, [])
            if (updated_info is None):
                updated_info = (ship.x, ship.y, ship.speed, ship.orientation, [])
            if (ship.team == 0):
                en_v_list.extend(ship.projected_vList)
            else:
                my_v_list.extend(ship.projected_vList)
            cur_info = ((updated_info[0], updated_info[1]), updated_info[2], updated_info[3], ship.rum, ship.canFire, ship.canMine, ship.team)
            if (ship.team == 1):
                my_ship_end_info.append(((updated_info[0], updated_info[1]), updated_info[3]))
            shipsInfo.append(cur_info)
        for info in shipsInfo:
            spaces = shipSpace(info[0][0], info[0][1], info[2])
            for space in spaces:
                cur_key = locToKey(space)
                if (cur_key not in occ_list):
                    occ_list.append(cur_key)
        
        available_actions = [Wait(), Slower(), Faster(), Port(), Starboard()]
        destroyed = False
        init_rum = self.rum

        # Project self location
        for action in available_actions:
            if (destroyed):
                continue
            projectionResult = verifyMove((self.x, self.y), self.speed, self.orientation, action, occ_list)
            if (projectionResult is None):
                continue
            projected_rum = init_rum - 1
            projected_x = projectionResult[0]
            projected_y = projectionResult[1]
            projected_speed = projectionResult[2]
            projected_orien = projectionResult[3]
            projected_v_list = projectionResult[4]
            projected_mid = (projected_x, projected_y)
            projected_bow = precomp_adjCell[projected_mid[0]+OFFSET_ADJCELL][projected_mid[1]+OFFSET_ADJCELL][projected_orien][0]
            projected_stern = precomp_adjCell[projected_mid[0]+OFFSET_ADJCELL][projected_mid[1]+OFFSET_ADJCELL][projected_orien][1]
            projected_key = locToKey(projected_mid)
            # Project self's destruction if any
            # MINE
            for key in projected_v_list:
                if (key in mine_key_list):
                    projected_rum -= 25
            # CANNONBALL
            if (verifyLoc(projected_bow)):
                curFires = cannonGrid[projected_bow[0]][projected_bow[1]].values()
                if (len(curFires) > 0):
                    for fire in curFires:
                        if (fire.ttt == 1):
                            projected_rum -= 25
            if (verifyLoc(projected_stern)):
                curFires = cannonGrid[projected_stern[0]][projected_stern[1]].values()
                if (len(curFires) > 0):
                    for fire in curFires:
                        if (fire.ttt == 1):
                            projected_rum -= 25
            if (verifyLoc(projected_mid)):
                curFires = cannonGrid[projected_mid[0]][projected_mid[1]].values()
                if (len(curFires) > 0):
                    for fire in curFires:
                        if (fire.ttt == 1):
                            projected_rum -= 50
            # Account for adjacent exploding mines :O
            adjCells = adjacentShipCells(projected_mid, projected_orien)
            for cell in adjCells[0]: # Use the loc list
                if (verifyLoc(cell) and locToKey(cell) in mine_key_list):
                    curFires = cannonGrid[cell[0]][cell[1]].values()
                    if (len(curFires) > 0):
                        for fire in curFires:
                            if (fire.ttt == 1):
                                projected_rum -= 10
            # Ship will be destroyed next turn
            if (projected_rum <= 0):
                # Check if is close enough to sacrifice self
                if (self.rum < 32 and tgtShip.rum+min(self.rum-2, 30) <= 104 and (projected_key in my_v_list or precomp_distTo[moveLoc[0]][moveLoc[1]][projected_mid[0]][projected_mid[1]] < 5) and projected_key not in en_v_list):
                    destroyed = True
                    sacrifice_move = action
                # Hidden else statement:
                #   sacrifice_move = None
                #   -> Goes into finding an optimal path to reach targeted destination instead

        # Won't be destroyed next turn (self-destruct)
        #BUG:   There's a bug here that would result in inaccurate firing of cannon, delaying sacrifice
        #       and potentially wasting rum! :O I'll leave you to fix it...
        projectionResult = verifyMove((self.x, self.y), self.speed, self.orientation, Wait(), occ_list)
        projected_mid = (projectionResult[0], projectionResult[1])
        projected_key = locToKey(projected_mid)
        if (self.rum < 32 and tgtShip.rum+min(self.rum-2, 30) <= 104 and (not destroyed) and ((projected_key in my_v_list or precomp_distTo[moveLoc[0]][moveLoc[1]][projected_mid[0]][projected_mid[1]] < 5) and projected_key not in en_v_list)):
            sacrifice_move = Fire(projected_mid[0], projected_mid[1])

        # Resume pathing if not yet suitable to sacrifice
        if (sacrifice_move is None):
            # Prepare potential mines
            potential_mines = []
            for ship in [enShip for enShip in ships.values() if enShip.team == 0]:
                potential_mines.extend(ship.projected_mineKeys)
            bfs_result = None #TODO: BFS here
            if (bfs_result is not None):
                self.curMove = bfs_result[0]
                return bfs_result[0].printCmd()
            else:
                self.curMove = Wait()
                return "WAIT"
        else:
            self.curMove = sacrifice_move
            return sacrifice_move.printCmd()
        return self.curMove.printCmd()

    def turn(self):
        init_t = time.time()
        self.curMove = Wait()
        # Currently occupied spaces
        orig_spaces = shipSpace(self.x, self.y, self.orientation)
        barrels_loc_list = [(barrel.x, barrel.y) for barrel in barrels.values()]
        barrels_key_list = [locToKey(loc) for loc in barrels_loc_list]

        # Precompute occupancy
        shipsInfo = []
        occ_list = []
        en_v_list = []
        my_ship_end_info = []
        for ship in ships.values():
            if (ship.ID == self.ID):
                continue
            updated_info = verifyMove((ship.x, ship.y), ship.speed, ship.orientation, ship.curMove, [])
            if (updated_info is None):
                updated_info = (ship.x, ship.y, ship.speed, ship.orientation, [])
            if (ship.team == 0):
                en_v_list.extend(updated_info[4])
            cur_info = ((updated_info[0], updated_info[1]), updated_info[2], updated_info[3], ship.rum, ship.canFire, ship.canMine, ship.team)
            if (ship.team == 1):
                my_ship_end_info.append(((updated_info[0], updated_info[1]), updated_info[3]))
            shipsInfo.append(cur_info)
        for info in shipsInfo:
            spaces = shipSpace(info[0][0], info[0][1], info[2])
            for space in spaces:
                cur_key = locToKey(space)
                if (cur_key not in occ_list):
                    occ_list.append(cur_key)

        # BFS-Search to next barrel
        bfs_t = time.time()
        wait_score = 0
        # Prepare ignore barrel list to distribute targets
        ignore_barrels = []
        if (self.closestBarrelKey not in barrels_key_list):
            # No barrels in sight
            ignore_barrels = [ship.closestBarrelKey for ship in ships.values() if ship.team == 1 and ship.closestBarrelKey in barrels_key_list]

        # Prepare potential mines
        potential_mines = []
        for ship in [enShip for enShip in ships.values() if enShip.team == 0]:
            potential_mines.extend(ship.projected_mineKeys)

        bfs_result = findSpace((self.x, self.y, self.speed, self.orientation), self.lamb_target, BFS_SEARCH_DEPTH, occ_list, ignore_barrels, potential_mines)
        
        print >> sys.stderr, bfs_result
        action = None
        ttt_barrel = None
        target_location = None
        if (bfs_result is not None):
            action = bfs_result[0]
            wait_score = bfs_result[1]
            ttt_barrel = bfs_result[2]
            target_location = bfs_result[3]
            print >> sys.stderr, "BFS ACTION: {} | Wait Score: {}".format(action.printCmd(), wait_score)

        print >> sys.stderr, "BFS Complete :D {}".format(time.time()-bfs_t)

        # Stop just short of barrel to maximize rum expliotation :D
        if (ttt_barrel is not None and STOP_SHORT_BARRELS):
            print >> sys.stderr, "My Max Rum: {} | En Max Rum: {}".format(MY_MAX_RUM, EN_MAX_RUM)
            if (verifyLoc(target_location) and gameGrid[target_location[0]][target_location[1]] == BARREL):
                cur_targeted_barrel = barrels[gameGridID[target_location[0]][target_location[1]]]
                if (cur_targeted_barrel is not None and numBarrels <= len(ships.values())): # Be more aggressive early-game!
                    # Ignore waiting if enemy can get to it first :O
                    enShips = [ship for ship in ships.values() if ship.team == 0]
                    en_v_list = []
                    for ship in enShips:
                        en_v_list.extend(ship.projected_vList)
                    if (locToKey(target_location) not in en_v_list):
                        if (ttt_barrel <= 2 and self.rum + cur_targeted_barrel.rum > 100):
                            print >> sys.stderr, "STOPPING SHORT OF BARREL: {} | rum: {}".format(self.rum, cur_targeted_barrel.rum)
                            if (self.speed == 2):
                                slower_result = verifyMove((self.x, self.y), self.speed, self.orientation, Slower(), occ_list)
                                # Check for cannonballs
                                underFire = False
                                occupiedSpaces = shipSpace(slower_result[0], slower_result[1], slower_result[3])
                                for space in occupiedSpaces:
                                    if (verifyLoc(space)):
                                        curFires = cannonGrid[space[0]][space[1]].values()
                                        if (len(curFires) > 0):
                                            for fire in curFires:
                                                if (fire.ttt <= DELAY_CANNONBALL):
                                                    underFire = True
                                if (not underFire):
                                    action = Slower()
                            elif (ttt_barrel <= 0):
                                if (self.speed > 0):
                                    slower_result = verifyMove((self.x, self.y), self.speed, self.orientation, Slower(), occ_list)
                                    # Check for cannonballs
                                    underFire = False
                                    occupiedSpaces = shipSpace(slower_result[0], slower_result[1], slower_result[3])
                                    for space in occupiedSpaces:
                                        if (verifyLoc(space)):
                                            curFires = cannonGrid[space[0]][space[1]].values()
                                            if (len(curFires) > 0):
                                                for fire in curFires:
                                                    if (fire.ttt <= DELAY_CANNONBALL):
                                                        underFire = True
                                    if (not underFire):
                                        action = Slower()
                                else:
                                    wait_result = verifyMove((self.x, self.y), self.speed, self.orientation, Wait(), occ_list)
                                    # Check for cannonballs
                                    underFire = False
                                    occupiedSpaces = shipSpace(wait_result[0], wait_result[1], wait_result[3])
                                    for space in occupiedSpaces:
                                        if (verifyLoc(space)):
                                            curFires = cannonGrid[space[0]][space[1]].values()
                                            if (len(curFires) > 0):
                                                for fire in curFires:
                                                    if (fire.ttt <= DELAY_CANNONBALL):
                                                        underFire = True
                                    if (not underFire):
                                        action = Wait()
                            print >> sys.stderr, "STOPPING SHORT OF BARREL -> {}".format(action.printCmd())

        # Move
        if (isinstance(action, Wait)):
            # If WAIT, explore using MINE or FIRE
            fired = False
            mined = False
            myShips = [ship for ship in ships.values() if ship.team == 1]
            myShips_range = []
            for ship in myShips:
                myShips_range.extend(ship.projected_vList)
            enShips = [ship for ship in ships.values() if ship.team == 0]
            enShips_range = []
            for ship in enShips:
                enShips_range.extend(ship.projected_vList)
            
            end_result = verifyMove((self.x, self.y), self.speed, self.orientation, action, occ_list)
            end_spaces = shipSpace(end_result[0], end_result[1], end_result[3])
            end_spaces_keyList = (locToKey(end_spaces[0]), locToKey(end_spaces[1]), locToKey(end_spaces[2]))
            my_ship_end_info.append((end_spaces[1], end_result[3]))
            if (self.canFire == 0):
                tgtLoc = None
                # Target barrels enemies will get to first
                if (not fired):
                    # Cycle through barrels and find which enemy will get to first ;)
                    best_dist = 999999999
                    best_target = None
                    for barrel_key in barrels_key_list:
                        if (barrel_key in enShips_range and barrel_key not in myShips_range):
                            # Valid target Score and keep
                            cur_dist = 999999999
                            cur_target = keyToLoc(barrel_key)
                            if (verifyLoc(orig_spaces[0])):
                                cur_dist = precomp_distTo[orig_spaces[0][0]][orig_spaces[0][1]][ship.x][ship.y]
                            else:
                                cur_dist = distTo(orig_spaces[0][0], orig_spaces[0][1], ship.x, ship.y)
                            if (cur_dist < best_dist and len(cannonGrid[cur_target[0]][cur_target[1]].values()) < 1):
                                best_dist = cur_dist
                                best_target = cur_target
                    if (best_target is not None and best_dist <= 10):
                        self.canFire = DELAY_FIRE
                        fired = True
                        print >> sys.stderr, "Destroying Barrel! | Target: {} | Dist: {}".format(best_target, best_dist)
                        return "FIRE {} {}".format(best_target[0], best_target[1])

                # Target enemies
                if (not fired):
                    best_dist = 999999999
                    best_target = None
                    for ship in enShips:
                        # Hardcoded cases
                        cur_dist = precomp_distTo[orig_spaces[1][0]][orig_spaces[1][1]][ship.x][ship.y]
                        if (cur_dist <= 2):
                            if (ship.speed == 0):
                                best_target = (ship.x, ship.y)
                                best_dist = -999 # Pick me!
                                fired = True
                                break
                            else:
                                # Look ahead to see if they are going to collide ==> speed is effectively 0
                                en_bow = cellAhead((ship.x, ship.y), ship.orientation)
                                en_ahead_bow = cellAhead(en_bow, ship.orientation)
                                # Check crashed into objects (MINES included :D)
                                if (verifyLoc(en_ahead_bow) and gameGrid[en_ahead_bow[0]][en_ahead_bow[1]] != 0 and gameGrid[en_ahead_bow[0]][en_ahead_bow[1]] != BARREL):
                                    best_target = (ship.x, ship.y)
                                    best_dist = -999 # Pick me!
                                    fired = True
                                    break
                                elif (not verifyLoc(en_ahead_bow)): # Crashed into boundaries
                                    best_target = (ship.x, ship.y)
                                    best_dist = -999 # Pick me!
                                    fired = True
                                    break
                        # General Case
                        en_positions = ship.scored_projection
                        if (len(en_positions) < 1):
                            print >> sys.stderr, "Error: Enemy ships does not occupy any positions o.O?"
                            continue
                        cur_target = keyToLoc(en_positions[0][1])
                        if (en_positions[0][1] in end_spaces_keyList):
                            continue
                        cur_dist = 0
                        if (verifyLoc(orig_spaces[0])):
                            cur_dist = precomp_distTo[orig_spaces[0][0]][orig_spaces[0][1]][cur_target[0]][cur_target[1]]
                        else:
                            cur_dist = distTo(orig_spaces[0][0], orig_spaces[0][1], cur_target[0], cur_target[1])
                        if (cur_dist < best_dist and len(cannonGrid[cur_target[0]][cur_target[1]].values()) < 1):
                            best_dist = cur_dist
                            best_target = cur_target
                    if (best_target is not None and best_dist <= 7):
                        self.canFire = DELAY_FIRE
                        fired = True
                        print >> sys.stderr, "Firing cannon! {} | Bow: {} | Target: {} | Dist: {}".format(fired, orig_spaces[0], best_target, best_dist)
                        return "FIRE {} {}".format(best_target[0], best_target[1])

                # Target mines
                if (not fired):
                    avoid_firing_keys = []
                    for info in my_ship_end_info:
                        cur_adj_cells = adjacentShipCells(info[0], info[1])
                        avoid_firing_keys.extend(cur_adj_cells[1])
                    for mine in mines.values():
                        if (fired):
                            continue
                        curDist = 0
                        if (verifyLoc(orig_spaces[0])):
                            curDist = precomp_distTo[orig_spaces[0][0]][orig_spaces[0][1]][mine.x][mine.y]
                        else:
                            curDist = distTo(orig_spaces[0][0], orig_spaces[0][1], mine.x, mine.y)
                        if (curDist <= 10):
                            cur_mine_loc = (mine.x, mine.y)
                            print >> sys.stderr, "TARGETING MiNE: {}".format(cur_mine_loc)
                            curKey = locToKey(cur_mine_loc)
                            adj_keys = [locToKey(loc[0]) for loc in precomp_adjCell[cur_mine_loc[0]+OFFSET_ADJCELL][cur_mine_loc[1]+OFFSET_ADJCELL]]
                            print >> sys.stderr, adj_keys
                            nearby_barrels = [key for key in adj_keys if key in barrels_key_list]
                            print >> sys.stderr, nearby_barrels
                            if (curKey not in avoid_firing_keys and len(nearby_barrels) < 1 and len(cannonGrid[cur_mine_loc[0]][cur_mine_loc[1]].values()) < 1):
                                self.canFire = DELAY_FIRE
                                fired = True
                                print >> sys.stderr, "Firing cannon!"
                                return "FIRE {} {}".format(cur_mine_loc[0], cur_mine_loc[1])

            if (not fired and self.canMine == 0):
                # Mine if enemy will occupy space directly behind stern and self.speed > 0
                tmp_mine_loc = cellBehind(orig_spaces[2], self.orientation)
                tmp_mine_locKey = locToKey(tmp_mine_loc)
                if (tmp_mine_locKey in en_v_list and self.speed > 0):
                    self.canMine = DELAY_MINE
                    mined = True
                    print >> sys.stderr, "Dropping mine"
                    return "MINE"

            if (not fired and not mined): # Revert to default command
                self.curMove = action
                return action.printCmd()
        else:
            self.curMove = action
            return action.printCmd()
        return self.curMove.printCmd()

gameGrid = [[0 for i in xrange(21)] for j in xrange(23)]
gameGridID = [[-1 for i in xrange(21)] for j in xrange(23)]
cannonGrid = [[dict() for i in xrange(21)] for j in xrange(23)]
ships = dict()
cannonballs = dict()
barrels = dict()
mines = dict()
predicted_mines = dict()
predicted_cannonballs = dict()
lamb = None
numBarrels = 0
roundCount = 0
EN_MAX_RUM = 0
EN_SUM_RUM = 0
MY_MAX_RUM = 0
MY_MIN_RUM = 0
MY_SUM_RUM = 0

# Do some precomputation of commonly accessed values
for x in xrange(23):
    for y in xrange(21):
        cur_dists = [[distTo(x, y, j, i) for i in xrange(21)] for j in xrange(23)]
        precomp_distTo[x][y] = cur_dists
for x in xrange(27):
    for y in xrange(25):
        for o in xrange(6):
            precomp_adjCell[x][y][o] = (cellAhead((x-OFFSET_ADJCELL, y-OFFSET_ADJCELL), o), cellBehind((x-OFFSET_ADJCELL, y-OFFSET_ADJCELL), o))

print >> sys.stderr, "INIT DONE: {}".format(time.time()-time_t)

# game loop
while True:
    time_t = time.time()
    gameGrid = [[0 for i in xrange(21)] for j in xrange(23)]
    numBarrels = 0
    EN_MAX_RUM = 0
    EN_SUM_RUM = 0
    MY_SUM_RUM = 0
    roundCount += 1
    for ship in ships.values():
        ship.alive = False
        ship.curMove = Wait()
        ship.curTargetedBarrel = None
        ship.sacrifice = False
    for barrel in barrels.values():
        barrel.alive = False
    for mine in mines.values():
        mine.alive = False
    for cannonball in cannonballs.values():
        cannonball.alive = False
    my_ship_count = int(raw_input())  # the number of remaining ships
    entity_count = int(raw_input())  # the number of entities (e.g. ships, mines or cannonballs)
    for i in xrange(entity_count):
        entity_id, entity_type, x, y, arg_1, arg_2, arg_3, arg_4 = raw_input().split()
        entity_id = int(entity_id)
        x = int(x)
        y = int(y)
        arg_1 = int(arg_1)
        arg_2 = int(arg_2)
        arg_3 = int(arg_3)
        arg_4 = int(arg_4)
        gameGridID[x][y] = entity_id
        if (entity_type == "SHIP"):
            if (arg_4 == 1):
                gameGrid[x][y] = MYSHIP
                MY_SUM_RUM += arg_3
            else:
                gameGrid[x][y] = ENSHIP
                EN_SUM_RUM += arg_3
            if (entity_id in ships.keys()):
                ships[entity_id].update(arg_1, arg_2, arg_3, x, y)
            else:
                ships[entity_id] = Ship(entity_id, arg_1, arg_2, arg_3, arg_4, x, y)
            ships[entity_id].alive = True
            # Get enemy's maximum rum
            if (arg_4 == 0 and arg_3 > EN_MAX_RUM):
                EN_MAX_RUM = arg_3
            # Mark ship-occupied space on grid
            nx = x+hexAdj[y%2][ships[entity_id].orientation][0]
            ny = y+hexAdj[y%2][ships[entity_id].orientation][1]
            if (verifyLoc((nx, ny))):
                gameGrid[nx][ny] = OCCSHIP
            nx = x+hexAdj[y%2][(ships[entity_id].orientation-3)%6][0]
            ny = y+hexAdj[y%2][(ships[entity_id].orientation-3)%6][1]
            if (verifyLoc((nx, ny))):
                gameGrid[nx][ny] = OCCSHIP
        elif (entity_type == "BARREL"):
            gameGrid[x][y] = BARREL
            if (entity_id not in barrels.keys()):
                barrels[entity_id] = Barrel(entity_id, arg_1, x, y)
            barrels[entity_id].alive = True
            numBarrels += 1
        elif (entity_type == "CANNONBALL"):
            if (arg_2 > 0):
                if (entity_id not in cannonballs.keys()):
                    cannonballs[entity_id] = Cannonball(entity_id, arg_1, arg_2, x, y)
                    cannonGrid[x][y][entity_id] = cannonballs[entity_id]
                    ships[arg_1].canFire = DELAY_FIRE
                cannonballs[entity_id].alive = True
        elif (entity_type == "MINE"):
            gameGrid[x][y] = MINE
            if (entity_id not in mines.keys()):
                mines[entity_id] = Mine(entity_id, x, y)
            mines[entity_id].alive = True

    time_t = time.time()

    for barrel in barrels.values():
        barrel.tick()

    for mine in mines.values():
        mine.tick()

    for ship in ships.values():
        ship.tick()

    MY_MAX_RUM = 0
    MY_MIN_RUM = 101
    lamb = None
    topDog = None
    myShips = [ship for ship in ships.values() if ship.team == 1]
    enShips = [ship for ship in ships.values() if ship.team == 0]
    # Decide when to start sacrificing own ships
    for ship in myShips:
        if (ship.rum > MY_MAX_RUM):
            MY_MAX_RUM = ship.rum
            topDog = ship
        if (ship.rum < MY_MIN_RUM):
            MY_MIN_RUM = ship.rum
            lamb = ship
    if (len(myShips) > 1 and numBarrels == 0):
        if ((MY_MAX_RUM <= EN_MAX_RUM or MY_SUM_RUM <= EN_SUM_RUM) and MY_MIN_RUM <= 50): # Start sacrificing own ships :O
            lamb.sacrifice = True
            topDog.lamb_target = (lamb.x, lamb.y)

    # Precompute possible enemy locations
    for ship in ships.values():
        ship.project(3)

    for ship in myShips:
        ship.predictFires()

    #TODO: Resolve ship sacrifices to anticipate dropping of barrel => moves into position to grab it immediately

    print >> sys.stderr, "STARTING SHIPS: {}".format(time.time()-time_t)

    for ship in myShips:
        tmp_t = time.time()
        outputCmd = "WAIT"
        if (not ship.sacrifice):
            print >> sys.stderr, "===============SHIP {}===============".format(ship.ID)
            outputCmd = ship.turn()
        else:
            print >> sys.stderr, "===============OFFERING SHIP {}===============".format(ship.ID)
            outputCmd = ship.offer(topDog) + " SACRIFICE :O"
        print "{} {}".format(outputCmd, int((time.time()-tmp_t)*100000)/100.0)
        print >> sys.stderr, "SHIP COMPLETE: {}".format(time.time()-tmp_t)

    for ball in cannonballs.values():
        ball.tick()

    print >> sys.stderr, "TURN COMPLETE: {}".format(time.time()-time_t)

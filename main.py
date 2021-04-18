import panda3d.core as pc
from direct.showbase.ShowBase import ShowBase
from direct.gui.OnscreenText import OnscreenText
from direct.task import Task
from direct.interval.MetaInterval import Sequence
from direct.interval.LerpInterval import LerpFunc
from direct.interval.FunctionInterval import Func

from math import pi, sin, cos
from collections import deque
import sys
import os
import random


FLOOR_LENGTH = 20
NUM_FLOORS = 6
FLOOR_TIME = 1.5
INIT_VELO = 20
GRAVITY = 30
SPEED = 20 / 1.5
MIN_GAP = 18
PLACE_THRESHOLD = 0.6


class Game(ShowBase):
    def __init__(self):
        # Set up the window, camera, etc.
        ShowBase.__init__(self)

        self.setUpWindow()

        # initialize state values
        self.keyMap = {"jump": 0, "big": 0, "down": 0, "float": 0}
        self.isJump = False
        self.velocity = 0
        self.score = 0
        self.start = True

        self.cactCols = set()

        # import and load sound effects
        self.jumpSound = loader.loadSfx("assets/levels/jump.ogg")
        self.bigJumpSound = loader.loadSfx("assets/levels/bigjump.ogg")
        self.dieSound = loader.loadSfx("assets/levels/die.ogg")
        self.scoreSound = loader.loadSfx("assets/levels/score.ogg")

        # Load the dinosaur model
        self.loadDino()

        # Initialize the track
        self.initFloor()

        # Set up collision traverser and handler
        self.cTrav = pc.CollisionTraverser("travis")
        self.colQueue = pc.CollisionHandlerQueue()

        # TODO: Change this to a dictionary of floor index to list of cacti,
        # realistically just a single cactus probably or a tuple
        # self.cacti = []
        # self.loadCact(self.floors[2][0],0,15,0)

        # csCact = pc.CollisionCapsule(0, -1, 2, 0, -1, 4, 1.5)
        # self.cactCol = self.cacti[0].attachNewNode(pc.CollisionNode('cnodeCact'))
        # self.cactCol.node().addSolid(csCact)
        # # self.cactCol.show()

        # Attach collision objects to models
        csHead = pc.CollisionSphere(1.65, 2.7, 2.8, 1.2)
        headCol = self.attachCollision(csHead, self.dino)
        # headCol.show()
        csBody = pc.CollisionSphere(1.65, 0.19, 0.03, 2.5)
        bodyCol = self.attachCollision(csBody, self.dino)
        # bodyCol.show()

        # Add dino colliders to the collision traverser and show collisions
        self.cTrav.addCollider(headCol, self.colQueue)
        self.cTrav.addCollider(bodyCol, self.colQueue)
        self.cTrav.traverse(render)
        self.cTrav.show_collisions(render)

        # Add directional light in similar orientation to camera
        dlight = pc.DirectionalLight("my dlight")
        dlnp = render.attachNewNode(dlight)
        dlnp.setPos(30, -20, 14)
        dlnp.setHpr(40, -14, 0)
        render.setLight(dlnp)

        dlight1 = pc.DirectionalLight("my dlight1")
        dlight1.setColor((1, 1, 1, 1))
        dlight1.setSpecularColor((1, 1, 1, 1))
        dlnp1 = render.attachNewNode(dlight1)
        dlnp1.setPos(0, 20, 0)
        dlnp1.setHpr(0, 90, 0)
        render.setLight(dlnp1)

        # Add ambient light for improved color quality
        ambientLight = pc.AmbientLight("ambientLight")
        ambientLight.setColor((0.3, 0.3, 0.3, 1))
        ambientLightNP = render.attachNewNode(ambientLight)
        render.setLight(ambientLightNP)

        # Attach events to button clicks
        self.escapeEventText = self.genLabelText(1, "ESC: Quit")
        self.accept("escape", sys.exit)

        self.jumpEventText = self.genLabelText(2, "SPACE: Jump")
        self.accept("space", self.setKey, ["jump", True])
        self.accept("space-up", self.setKey, ["jump", False])

        self.bigEventText = self.genLabelText(3, "W: Big Jump")
        self.accept("w", self.setKey, ["big", True])
        self.accept("w-up", self.setKey, ["big", False])

        self.floatEventText = self.genLabelText(4, "D: Float")
        self.accept("d", self.setKey, ["float", True])
        self.accept("d-up", self.setKey, ["float", False])

        self.taskMgr.add(self.displayScore, "scoreTask")

        # Set the infinite scrolling track
        self.contFloor()

        self.taskMgr.add(self.move, "moveTask")
        self.taskMgr.add(self.collided, "collideTask")

    def setUpWindow(self):
        """ Set up window to be specified size """
        properties = pc.WindowProperties()
        properties.setSize(2000, 1500)
        self.win.requestProperties(properties)

        # Set background color to a cyan-like color
        self.win.setClearColor((0, 1, 1, 1))

        # Place and orient camera to face the track
        self.camera.setPos(30, -20, 14)  # x, y, z
        self.camera.setHpr(40, -14, 0)  # yaw, pitch, roll

        self.disableMouse()

    def loadDino(self):
        """ Load and place dino into environment w/ orientation and scale"""
        self.dino = self.loader.loadModel("assets/characters/dino1")
        self.dino.setPos(-1, 0, 2.5)
        self.dino.setHpr(0, 0, 0)
        self.dino.reparentTo(render)

    def loadCact(self, parent, x=0, y=15, z=-0.5):
        """Import and place cactus into environment
        Parameters:
        - parent: (floor, list) tuple
        - x,y,z: ints representing coordinates
        """
        cactus = self.loader.loadModel("assets/characters/bigCactus")
        cactus.setPos(x, y, z)
        cactus.setHpr(90, 0, 0)
        cactus.reparentTo(parent[0])
        parent[1].append(cactus)

    def attachCollision(self, colSol, parent):
        """Attach collision node to parent node
        - Returns: The collision node based on the collision solid
        """
        colNode = parent.attachNewNode(pc.CollisionNode("cnode"))
        colNode.node().addSolid(colSol)
        return colNode

    def genLabelText(self, i, text):
        """Creates an onscreentext on the top left for instructions
        Parameters:
        - i: index of instruction
        - text: the text to be displayed
        Returns:
        - An onscreen event text
        """
        return OnscreenText(
            text=text,
            parent=base.a2dTopLeft,
            scale=0.05,
            pos=(0.06, -0.065 * i),
            fg=(1, 1, 1, 1),
            align=pc.TextNode.ALeft,
        )

    def setKey(self, key, val):
        """ Sets keyMap dictionary value """
        self.keyMap[key] = val

    def initFloor(self):
        """ Creates queue of floors"""
        self.floors = deque()

        for i in range(NUM_FLOORS):
            floor_model = loader.loadModel("assets/levels/floor")
            # add floor, cacti list to queue of floors
            self.floors.append((floor_model, []))

            if i == 0:
                # if the floor is the first, set parent to render
                floor_model.setPos(0, -FLOOR_LENGTH, 0)
                floor_model.reparentTo(render)
            else:
                # set parent of this floor to the earlier floor
                floor_model.setPos(0, FLOOR_LENGTH, 0)
                floor_model.reparentTo(self.floors[-2][0])

    def move(self, task):
        """ Handles key events"""
        dt = globalClock.getDt()  # dt is the change in time from last call
        if self.keyMap["big"] and not self.isJump:
            # if just pressed key for big jump
            self.isJump = True
            self.velocity = INIT_VELO * 1.25
            self.dino.setZ(self.dino, self.velocity * dt)
            self.bigJumpSound.setVolume(1)
            self.bigJumpSound.play()
        elif self.keyMap["jump"] and not self.isJump:
            # if just pressed key for regular jump
            self.isJump = True
            self.velocity = INIT_VELO
            self.dino.setZ(self.dino, self.velocity * dt)
            self.jumpSound.setVolume(0.75)
            self.jumpSound.play()
        elif self.keyMap["float"] and self.isJump and self.velocity < 0:
            # if in jump, falling, and pressed key for floating
            self.velocity = self.velocity - (GRAVITY / 3) * dt
            new_pos = self.dino.getZ() + (self.velocity * dt)
            if new_pos > 2.5:
                self.dino.setZ(self.dino, self.velocity * dt)
            else:
                self.isJump = False
                self.velocity = 0
        elif self.isJump:
            # else if in a jump, we change the z value of the dino
            self.velocity = self.velocity - GRAVITY * dt
            new_pos = self.dino.getZ() + (self.velocity * dt)
            if new_pos > 2.5:
                self.dino.setZ(self.dino, self.velocity * dt)
            else:
                self.isJump = False
                self.velocity = 0
        return Task.cont

    def collided(self, task):
        """Checks for collisions, ends game if senses one"""
        if self.colQueue.getNumEntries() > 0:
            sys.exit()
        return Task.cont

    def deleteCacti(self, parent):
        """Deletes cacti and removes all related objects from floor
        Parameters:
        - parent: (floor, cacti list) tuple
        """
        c_list = parent[1]
        for i in range(len(c_list)):
            c_list[i], temp = None, c_list[i]
            temp.node().removeAllChildren()
            temp.removeNode()

    def genCacti(self, previous, current):
        """Function to procedurally generate cacti (obstacles)
        Parameters:
        - previous: the earlier floor, cacti list tuple
        - current: the currect floor, cacti list tuple, where to generate
        """
        # use load cacti to place onto floor, then create collision boxes
        past_list = previous[1]
        end = FLOOR_LENGTH
        if len(past_list) == 0:  # if previous floor has no cacti obstacles
            start = 0
        else:  # if previous floor has cacti obstacles, find largest y val cactus
            # from the previous floor
            furthest = float("-inf"), None
            for cactus in past_list:
                if cactus.getY() > furthest[0]:
                    furthest = cactus.getY(), cactus
            # find the space between the last cacti in prev and new floor
            space = FLOOR_LENGTH - furthest[0]
            # ensures that the earliest cacti coord in current has enough space
            start = 0 if space >= MIN_GAP else MIN_GAP - space
        while end - start > MIN_GAP:
            # randomly place the cacti
            # determine position
            y = random.uniform(start, end)
            # decide if we want to place cactus or not
            if random.random() > PLACE_THRESHOLD:
                # load cactus
                self.loadCact(current, x=0, y=y, z=0)
                # put hitboxes
                csCact = pc.CollisionCapsule(0, -1, 2, 0, -1, 4, 1.5)
                cactCol = current[1][-1].attachNewNode(pc.CollisionNode("cnodeCact"))
                cactCol.node().addSolid(csCact)
                start = y + MIN_GAP
            else:
                start = y + MIN_GAP / 2
            # update start to new position

    def contFloor(self):
        """ Function to continously update (move) the floor"""
        recycle = self.floors.popleft()  # recycle is a (floor,list) pair
        self.deleteCacti(recycle)
        recycle = recycle[0], []
        self.genCacti(
            self.floors[-1], recycle
        )  # generates new list of cacti for recycle

        first_floor = self.floors[0][0]
        first_floor.setY(0)

        first_floor.reparentTo(render)

        recycle[0].reparentTo(self.floors[-1][0])
        recycle[0].setY(FLOOR_LENGTH)
        self.floors.append(recycle)

        self.floorMove = Sequence(
            LerpFunc(
                self.floors[0][0].setY,
                duration=FLOOR_TIME,
                fromData=0,
                toData=-FLOOR_LENGTH,
            ),
            Func(self.contFloor),
        )
        self.floorMove.start()

    def displayScore(self, task):
        """ Function to display the score continuously on top right of the screen"""
        if self.start:
            self.disp_score = OnscreenText(
                text="Score: " + str(int(self.score)),
                parent=base.a2dTopRight,
                scale=0.075,
                pos=(-0.1, -0.08),
                fg=(1, 1, 1, 1),
                align=pc.TextNode.ARight,
                mayChange=True,
            )
            self.start = False
        else:
            self.disp_score.setText("Score: " + str(int(self.score)))
            if int(self.score) % 100 == 0 and int(self.score) > 0:
                self.scoreSound.setVolume(0.4)
                self.scoreSound.play()
        self.score = task.time * SPEED
        return Task.cont

    def spinCameraTask(self, task):
        """ Function to continuously sin the camera"""
        angleDegrees = task.time * 6.0
        angleRadians = angleDegrees * (pi / 180.0)
        self.camera.setPos(20 * sin(angleRadians), -20 * cos(angleRadians), 3)
        self.camera.setHpr(angleDegrees, 0, 0)
        return Task.cont


app = Game()
app.run()
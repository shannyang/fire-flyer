import pygame
import random
from pygame.locals import *
import math
import shelve
import os
from Classes import *
from Level import *
from GlobalFunctions import *

class ComputerLevel(TwoPlayerLevel):

    # Although a subclass of TwoPlayerLevel, this is used for 1P boss battle

    # Depending on current state, the computer player either moves towards
    # target coordinates, or executes moves from a queue.

    def keyPressed(self, event):
        if event.key == pygame.K_SPACE and self.BossInstructions:
            self.BossInstructions = False
            self.mode = None
        if event.key == pygame.K_p and self.mode != 'Over':
            if self.mode != "Pause":
                self.mode = "Pause"
            else: self.mode = None
        elif event.key == pygame.K_t:
            self.mode = 'Over'
        if self.mode == None:
            if event.key == pygame.K_RIGHT:
                self.player1.walk(1)
            elif event.key == pygame.K_LEFT:
                self.player1.walk(-1)
            elif event.key == pygame.K_UP or event.key == pygame.K_SPACE:
                self.player1.jump()

    def timerFired(self):
        if self.mode == 'next':
            return True
        if self.mode == None:
            if self.movesClock % 4 == 0:
                # with 20 fps, this should update around 5 times per second
                self.updateComputerPlayer()
            self.movesClock += 1
        super(ComputerLevel, self).timerFired()

    def handleCollisions(self):
        self.handlePlatformCollisions()
        self.enemyCollisions()
        self.newBlock()
        self.handlePowerUps()
        self.setPowerUps()
        self.adjustBlocks()
        self.clearOldSprites()
        if self.player1.lives == 0 or self.blockCounter == self.maxBlocks:
            self.mode = 'Lost'
        elif self.player2.lives == 0:
            self.mode = 'Over'

    def updateComputerPlayer(self):
        if self.currentBlock != None and self.currentBlock.dropType == 2:
            self.advanceMove()
            # Try to get drop to hit player, since risk to self is low
        else:
            # Touching the drop will hurt it - try to evade
            self.passiveMove()
        self.preventFalls()

    def advanceMove(self):
        # Firedrop is coming; try to hit the player
        self.getTargetLocation()
        if self.movesList != []:
            # Proceed with queue
            self.executeMove()
            self.getTargetLocation()
        elif self.target != None:
            # No queued moves, an offensive on the opponent
            self.approachTarget()
        else:
            # No immediate threat or opportunity for attack - maintain
            self.platformBalance()

    def passiveMove(self):
        if self.movesList != []:
            self.executeMove()
        elif self.currentBlock != None:
            self.emergencyEvade()
            self.avoidBlock()
            self.approachTarget()
        self.platformBalance()

    def executeMove(self):
        # 0 = jump, 1 or -1 = direction for walking
        command = self.movesList.pop(0)
        if command == 0:
            self.player2.jump()
        elif command == 1 or command == -1:
            self.player2.walk(command)


    #############################
    # Targeting
    #############################

    # Sort platforms by rough likelihood of being hit by the raindrop next
    # Go through sorted list until one of them has a "line" to the oponent
    # Set target to angle the platform towards the opponent

    def approachTarget(self):
        # Computer can make one move towards set target, 4 times a second
        marginY = 15
        marginX = 20
        targetX, targetY = self.target
        playerCx, playerCy = self.player2.rect.center
        # Decide whether to jump or walk
        if (playerCy - targetY > marginY) and self.player2.jumpStep < 2:
            # Because of gravity, it's okay to be above the target
            self.player2.jump()
        elif abs(playerCx - targetX) > marginX:
            dx = abs(targetX - playerCx)/(targetX - playerCx)
            self.player2.walk(dx)
        self.getTargetLocation()

    def getTargetLocation(self):
        platform, direction = self.getTargetPlatform()
        if platform == None:
            self.target = None
        else:
            # Target a point on left or right of platform,
            # depending on the angle wanted
            moveRange = random.randint(20, 30)
            targetX = platform.cx + moveRange*direction
            self.target = (targetX, platform.cy)

    def getTargetPlatform(self):
        # Picks a platform as "close" to the raindrop as possible
        # where the platform can be angled towards an opponent
        toCheck = self.sortPlatforms()
        targetPlatform = None
        direction = None
        for platform in toCheck:
            if self.lineToEnemy(platform) != None:
                targetPlatform = platform
                direction = self.lineToEnemy(platform)
                break # Only want first platform for which this works
        return targetPlatform, direction

    def lineToEnemy(self, platform):
        # Checks whether enemy is within reach of the platform
        # Returns -1 if enemy is to the left, 1 if to the right
        # None if the enemy cannot be reached
        margin = 30
        xmax, ymax = self.screenSize
        opponentCx, opponentCy = self.player1.rect.center
        # Calculate current angle of opponent
        yLine = abs(opponentCy - platform.cy)
        xLine = opponentCx - platform.cx
        if xLine != 0:
            tangent = float(yLine)/abs(xLine)
            angle = math.atan(tangent)
            angle = int(math.degrees(angle)) # in whole degrees
            if angle < platform.maxAngle + margin:
                return abs(xLine)/xLine

    def sortPlatforms(self):
        blockRect = self.currentBlock.rect
        candidates = []
        for platform in self.platforms:
            upperMargin = 100
            if platform.cy + upperMargin >= blockRect.bottom:
                # Excludes platforms above the falling block
                candidates += [platform]
        candidates = sorted(candidates, self.heuristicCmp)
        return candidates

    def heuristicCmp(self, platform1, platform2):
        # Compares platforms by how likely the raindrop is to fall on each next
        p1 = self.heuristicConstant(platform1)
        p2 = self.heuristicConstant(platform2)
        return cmp(p1, p2)

    def heuristicConstant(self, platform):
        # Manhattan distance from drop's projected center to platform center
        result = 0
        framesToProject = 5
        blockCx, blockCy = self.currentBlock.rect.center
        blockCx += framesToProject*self.currentBlock.vx
        blockCy += framesToProject*self.currentBlock.vy
        blockDistance = platform.cx - blockCx
        verticalDistance = platform.cy - blockCy
        dropPlatform = self.platformsHit(self.currentBlock)
        result += (abs(blockDistance) + abs(verticalDistance))
        return result

    def isInDirection(self, platform):
        # Returns whether the falling block is going towards the platform
        blockCx, blockCy = self.currentBlock.rect.center
        blockDistance = platform.cx - blockCx
        if self.currentBlock.vx == 0:
            block_dx = 0
        else:
            # get unit with same sign as velocity of block
            block_dx = abs(self.currentBlock.vx)/self.currentBlock.vx
        if blockDistance == 0:
            normalizedDistance = blockDistance
        else:
            # determine direction of platform relative to block
            normalizedDistance = abs(blockDistance)/blockDistance
        return block_dx == 0 or normalizedDistance == block_dx

    #########################
    # Balancing/Evasion
    #########################

    def preventFalls(self):
        # If not over the main platform, move back towards the center
        playerCx, playerCy = self.player2.rect.center
        platformList = self.platformsHit(self.player2)
        mainRect = self.mainPlatform.rect
        framesToProject = 5
        projectedX = playerCx + framesToProject*self.player2.vx
        if not mainRect.collidepoint(projectedX, self.mainPlatform.cy):
            # Uses a point on the platform with the same x as the projection
            # Then player's projected position is not above the main platform
            distance = playerCx - self.mainPlatform.cx
            oldDir = abs(distance)/distance
            self.player2.walk(-oldDir)
            self.movesList = [0, 0]

    def platformBalance(self):
        playerCx, playerCy = self.player2.rect.center
        platformList = self.platformsHit(self.player2)
        mainRect = self.mainPlatform.rect
        framesToProject = 5
        projectedX = playerCx + framesToProject*self.player2.vx
        if platformList != []:
            # Player is on a platform
            platform = platformList[0] # there should be exactly one
            distance = playerCx - platform.cx
            if abs(self.player2.vx) >= 10 or abs(distance) > 30:
                self.movesList = self.platformBalanceMoves(platform)

    def emergencyEvade(self):
        # Creates a small precollision rect around the computer player's piece
        # This detects and avoid imminent collisions (short range)
        playerX, playerY = self.player2.rect.topleft
        margin = 100
        collideRect = Rect(playerX-margin, playerY-margin, 2*margin, 2*margin)
        if pygame.Rect.colliderect(collideRect, self.currentBlock.rect):
            dx = playerX - self.currentBlock.rect.left
            self.evadeFallingBlock(playerX, playerY)
            return True # indicates that immediate evasion happened

    def evadeFallingBlock(self, x, y):
        vertDistance = y - self.currentBlock.rect.top
        dx = self.currentBlock.vx
        if dx != 0:
            # Normalize the velocity
            dx /= abs(self.currentBlock.vx)
            dx = int(dx)
        if vertDistance > 2*self.currentBlock.terminalVelocity:
            # Try to move under it before jumping
            self.movesList = [-dx, -dx, 0]
        elif vertDistance > self.currentBlock.terminalVelocity:
            self.movesList = [-dx, 0]
        elif dx != self.player2.dx and self.movingTowardsPlayer():
            # try to jump over a raindrop moving towards you
            self.movesList = [0, -dx]
        else:
            self.movesList = [0, dx]

    def movingTowardsPlayer(self):
        # Check if the block is closer to player after next update
        blockCx, blockCy = self.currentBlock.rect.center
        blockVx = self.currentBlock.vx
        playerCx, playerCy = self.player2.rect.center
        return abs((blockCx + blockVx) - playerCx) < abs(blockCx - playerCx)

    def avoidBlock(self):
        # Long-range evasion strategy - basically the opposite of advancing
        # Try to get to platform where raindrop is unlikely to fall
        blockCx, blockCy = self.currentBlock.rect.center
        platforms = self.avoidSortPlatforms()
        if platforms != []:
            maxDistance = None
            for platform in platforms:
                distance = abs(blockCx - platform.cx) + abs(blockCx - platform.cy)
                if maxDistance == None or maxDistance < distance:
                    targetPlatform = platform
                    maxDistance = distance
            self.target = (targetPlatform.cx, targetPlatform.cy)

    def avoidSortPlatforms(self):
        # Basically the opposite of the offensive sort
        # Doesn't exclude higher platforms
        blockRect = self.currentBlock.rect
        candidates = []
        for platform in self.platforms:
                candidates += [platform]
        candidates = sorted(candidates, self.heuristicCmp)
        return reverse(candidates)

    def platformBalanceMoves(self, platform):
        playerCx, playerCy = self.player2.rect.center
        dx = distance = int(playerCx - platform.cx)
        moves = [0]
        verticalMargin = 4*platform.height
        if abs(playerCy - platform.cy) > verticalMargin:
            moves += [0]
        if dx != 0:
            # Normalize
            dx = abs(dx)/dx
            # Decides how many times to move to balance
            movesToMake = ((abs(distance)/20)+1)
            moves += movesToMake*[-dx]
        # jump, then move towards center
        # if there are more than 4 moves, cut moves list short
        return moves[0:4]

    #######################
    # Level mechanics
    #######################

    # Boss level includes raindrops that hurt the enemy
    # and firedrops that hurt you.

    # Some features are more similar to 1P mode than 2P mode,
    # so there's lots of overriding

    def enemyCollisions(self):
        if self.currentBlock != None:
        # Boss loses lives when hit by raindrop
        # You lose lives when hit by the firedrop
            if pygame.sprite.collide_rect(self.player1, self.currentBlock):
                if self.currentBlock.dropType == 2:
                    self.player1.loseLife()
            if pygame.sprite.collide_rect(self.player2, self.currentBlock):
                if self.currentBlock.dropType == 1:
                    self.player2.loseLife()

    def redrawAll(self):
        if self.BossInstructions:
            self.screen.blit(self.bossScreen, self.bossSurfacePos)
            pygame.display.flip()
        else:
            super(ComputerLevel, self).redrawAll()

    def drawScore(self):
        scoreColor = (46,139,87)
        score = "Score: %d" % self.player1.score
        lives = "Lives: %d" % self.player1.lives
        blocks = self.maxBlocks - self.blockCounter
        blockText = "Drops remaining: %d/%d" % (blocks, self.maxBlocks)
        scoreDraw = self.consola_font.render(score, True, scoreColor)
        livesDraw = self.consola_font.render(lives, True, scoreColor)
        blocksDraw = self.consola_font.render(blockText, True, scoreColor)
        self.screen.blit(scoreDraw, self.scorePos)
        self.screen.blit(livesDraw, self.livesPos)
        self.screen.blit(blocksDraw, self.blocksPos)

    def newBlock(self):
        blocksDropped = self.maxBlocks - self.blockCounter
        width, height = self.screenSize
        blockLimit = 3
        if len(self.fallingBlocks) < blockLimit:
            if self.blockCounter == self.maxBlocks:
                self.mode = 'Over'
            else:
                # blockType alternates between 1 and 2, on each drop
                blockType = (blocksDropped % 2) + 1
                x = self.getDropLocation()
                if blockType == 1:
                    block = Raindrop(x, 0)
                else:
                    block = Firedrop(x, 0)
                self.allsprites.add(block)
                self.fallingBlocks.add(block)
                self.blockCounter += 1
                self.currentBlock = block

    def initBossScreen(self):
        bossImage, bossRect = load_image('Backgrounds/bosssurface.png')
        self.bossScreen = bossImage
        self.bossSurfacePos = (0,0)

    def run(self, size, screen, clock, p1 = None, p2 = None):
        self.screenSize = width, height = size
        self.screen = screen
        self.clock = clock
        self.init()
        self.player1 = p1
        self.player2 = None
        self.placePlayers()
        while self.mode != False:
            if self.timerFired() == False:
                return False
            elif self.timerFired() == True:
                return self.player1
            elif self.mode == 'Quit':
                return None
        return False

    def init(self):
        super(ComputerLevel, self).init()
        self.movesClock = 0
        self.target = None
        self.currentBlock = None
        self.BossInstructions = True
        self.mode = 'Pause'
        self.initBossScreen()
        self.movesList = []

import pygame
import random
from pygame.locals import *
import math
import shelve
import os
from Classes import *
from GlobalFunctions import *

# Basic 1P and 2P levels!
# Boss level with AI is in ComputerLevel.py

class GameLevel(object):

    # Player controls!

    def mousePressed(self, event):
        (x, y) = self.mousePos
        if self.mode == 'Pause':
            resume = True
            for button in self.pauseMenuSprites:
                if button.rect.collidepoint(x, y):
                    self.runButton(button.eventName)
                    resume = False
            if resume == True:
                self.mode = None
        elif self.mode == 'Over' or self.mode == 'Lost':
            # For now this is the same as pause
            for button in self.pauseMenuSprites:
                if button.rect.collidepoint(x, y):
                    self.runButton(button.eventName)
        elif self.mode == 'Won':
            for button in self.winMenuSprites:
                if button.rect.collidepoint(x, y):
                    self.runButton(button.eventName)

    def runButton(self, eventName):
        if eventName == 'retry':
            self.retryLevel()
        elif eventName == 'quit':
            self.mode = 'Quit'
        elif eventName == 'nextLevel':
            self.resetPlayer()
            self.mode = 'next'
            # Temp mode that tells TimerFired to return the player

    def resetPlayer(self):
        # Because 2P mode has a different reset player
        self.player.reset()

    def retryLevel(self):
        width, height = self.screenSize
        self.mode = None # Unpauses
        score = self.player.score
        self.player.kill()
        self.player = None # Resets so that we can make a new "player"
        self.init()
        self.placePlayer(width/2, height/2)
        self.player.score = score

    def keyPressed(self, event):
        if event.key == pygame.K_p and self.mode != 'Over':
            if self.mode != "Pause":
                self.mode = "Pause"
            else: self.mode = None
        elif event.key == pygame.K_t:
            self.mode = 'Won'
        elif event.key == pygame.K_g:
            self.powerUpCounter = self.powerUpInt - 1
        if self.mode == None and self.player != None:
            if event.key == pygame.K_RIGHT:
                self.player.walk(1)
            elif event.key == pygame.K_LEFT:
                self.player.walk(-1)
            elif event.key == pygame.K_UP or event.key == pygame.K_SPACE:
                self.player.jump()

    def timerFired(self):
        self.redrawAll()
        self.clock.tick(20)
        if self.mode == 'next':
            return True
            self.mode = False
        elif self.mode == None: # In gameplay
            self.allsprites.update()
            self.handleCollisions()
        self.mousePos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.mode = False
                return False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.mousePressed(event)
            elif event.type == pygame.KEYDOWN:
                self.keyPressed(event)

    # Update game elements at each frame:

    def handleCollisions(self):
        self.handlePlatformCollisions()
        self.enemyCollisions()
        self.newBlock()
        if self.player != None:
            self.handlePowerUps()
            self.setPowerUps()
        self.adjustBlocks()
        self.clearOldSprites()
        if self.player.lives == 0:
            self.player.kill()
            self.mode = "Over"
        elif len(self.enemies) == 0:
            blocksBonus = self.maxBlocks - self.blockCounter
            self.player.score += blocksBonus
            self.mode = 'Won'

    def clearOldSprites(self):
        # Manages any sprites that go off-screen
        width, height = self.screenSize
        for sprite in self.allsprites:
            if (sprite.rect.top > height):
                if sprite == self.player:
                    self.player.loseLife(True)
                else:
                    sprite.kill()
            elif (sprite.rect.left < 0 or sprite.rect.right > width):
                if sprite == self.player:
                    sprite.rect.left = sprite.rect.left % width
                else:
                    sprite.kill()

    def setPowerUps(self):
        self.powerUpCounter += 1
        # Get rectangular limits of where powerups can be placed
        (x1, x2) = self.levelData['powerupsX']
        (y1, y2) = self.levelData['powerupsY']
        if len(self.powerUps) == 0 and self.powerUpCounter == self.powerUpInt:
            x = random.randint(x1, x2)
            y = random.randint(y1, y2)
            self.newPowerUp(x, y)
            self.powerUpCounter = 0
            # Decide how long to wait before next powerup spawns:
            wait = random.randint(self.powerTimeMin, self.powerTimeMax)
            self.powerUpInt = wait

    # Collisions and more physics

    def handlePowerUps(self):
        power = None
        for powerup in self.powerUps:
            if pygame.sprite.collide_rect(powerup, self.player):
                self.player.reset()
                self.player.power = power = powerup.power
                powerup.kill()
        if power == 'Heavy':
            self.player.changeWeight(2) # doubles player weight
        elif power == "Light":
            self.player.changeWeight(0.5) # halves player weight
        elif power == "Fast":
            self.player.speed *= 2
            # This has no effect yet
        elif power == "Slow":
            self.player.speed /= 2
            # ALso no effect

    def handlePlatformCollisions(self):
        for platform in self.platforms:
            totalweight = 0
            for block in self.fallingBlocks:
                if self.isOnPlatform(block, platform):
                    totalweight += self.getBlockWeight(block, platform)
                    if block.onPlatform == False: # just landed
                        block.vy = 0
                        block.jumpStep = 0
                    block.onPlatform = True
            platform.adjustPlatformAngle(totalweight)
        for block in self.fallingBlocks:
            if self.platformsHit(block) == []:
                block.onPlatform = False

    def enemyCollisions(self):
        for enemy in self.enemies:
            if not enemy.block:
                hitList = pygame.sprite.spritecollide(enemy,
                    self.fallingBlocks, False)
                for block in hitList:
                    if block == self.player and not self.player.block:
                        self.player.loseLife()
                        enemy.loseLife()
                    elif block != self.player:
                        enemy.loseLife()
                if enemy.lives == 0:
                    enemy.kill()
                    self.player.score += 1

    def platformsHit(self, block):
        hitList = []
        for platform in self.platforms:
            if self.isOnPlatform(block, platform):
                hitList += [platform]
        return hitList

    def isOnPlatform(self, block, platform):
        # Compares y-location to calculated point on platform
        # and checks whether the block will hit the platform at the next frame
        y = self.getY(block, platform)
        blockCx, blockCy = block.rect.center
        if blockCx < platform.rect.left or blockCx > platform.rect.right:
            return False
        return ((block.rect.bottom - y) < block.terminalVelocity and
            abs(y - block.rect.bottom) < platform.height)

    def getY(self, block, platform):
        # Returns what the y-value of the block would be (within some error)
        # if it were on the platform.
        blockCx, blockCy = block.rect.center
        dx = blockCx - platform.cx
        y = platform.cy - (dx*math.tan(platform.angle*math.pi/180))
        return y - platform.height/2

    def adjustBlocks(self):
        for block in self.fallingBlocks:
            platformsHit = self.platformsHit(block)
            if platformsHit == []:
                # return to normal!
                block.targetAngle = -block.angle/14.0
            else:
                for platform in platformsHit:
                    # should only have one
                    block.targetAngle = platform.angle - block.angle
                    block.vx -= platform.angle/30.0
                    if block.vy >= 0:
                        block.rect.bottom = self.getY(block, platform)

    def getBlockWeight(self, block, platform):
        # Calculates how much a block weighs down a platform
        blockCx, blockCy = block.rect.center
        distance = platform.cx - blockCx
        return block.weight * distance

    # Functions that make new game objects and add them to appropriate lists

    def newFireball(self, x, y, enemy = Fireball, lives = 3):
        fireball = enemy(x, y, lives)
        self.allsprites.add(fireball)
        self.enemies.add(fireball)

    def newPlatform(self, x, y, platform = Platform):
        newPlatform = platform(x, y)
        self.allsprites.add(newPlatform)
        self.platforms.add(newPlatform)

    def placePlayer(self, x, y):
        if self.player == None:
            # Create new player
            self.player = Player(x, y)
        else:
            self.player.rect.left = x
            self.player.rect.top = y
            self.player.fullReset()
        self.allsprites.add(self.player)
        self.fallingBlocks.add(self.player)

    def newBlock(self):
        # Creates new block from random drop location
        width, height = self.screenSize
        if len(self.fallingBlocks) < 2 and self.player != None:
            if self.blockCounter == self.maxBlocks:
                self.mode = 'Over'
            else:
                x = self.getDropLocation()
                block = Raindrop(x,0)
                self.allsprites.add(block)
                self.fallingBlocks.add(block)
                self.blockCounter += 1
                self.currentBlock = block

    def getDropLocation(self):
        # Requires that level data has a dropSpace key
        # Each entry in dropSpace is a range of legal drop positions
        xList = []
        for (x1, x2) in self.levelData['dropSpace']:
            sizeConstant = (abs(x1 - x2)/20)
            # Prevents small ranges from being overrepresented in random choice
            if sizeConstant < 1:
                sizeConstant = 1
            xList += [random.randint(x1, x2)]*sizeConstant
        return random.choice(xList)

    def newPowerUp(self, x, y):
        powerUp = PowerUp(x,y)
        self.allsprites.add(powerUp)
        self.powerUps.add(powerUp)

    # Drawing

    def redrawAll(self):
        self.screen.blit(self.background, (0,0))
        self.drawScore()
        for sprite in self.allsprites:
            self.screen.blit(sprite.image, (sprite.rect.x, sprite.rect.y))
        if self.mode == 'Pause':
            self.screen.blit(self.pauseSurface, self.pauseSurfacePos)
            self.pauseMenuSprites.draw(self.screen)
        elif self.mode == 'Over' or self.mode == 'Lost':
            self.screen.blit(self.lossSurface, self.lossSurfacePos)
            self.lossMenuSprites.draw(self.screen)
        elif self.mode == 'Won':
            self.screen.blit(self.winSurface, self.winSurfacePos)
            self.winMenuSprites.draw(self.screen)
        pygame.display.flip()

    def drawScore(self):
        scoreColor = (46,139,87)
        score = "Score: %d" % self.player.score
        lives = "Lives: %d" % self.player.lives
        blocks = self.maxBlocks - self.blockCounter
        blockText = "Drops remaining: %d/%d" % (blocks, self.maxBlocks)
        scoreDraw = self.consola_font.render(score, True, scoreColor)
        livesDraw = self.consola_font.render(lives, True, scoreColor)
        blocksDraw = self.consola_font.render(blockText, True, scoreColor)
        self.screen.blit(scoreDraw, self.scorePos)
        self.screen.blit(livesDraw, self.livesPos)
        self.screen.blit(blocksDraw, self.blocksPos)

    # Set up stuff

    def init(self):
        width, height = self.screenSize
        self.mode = None
        self.blockCounter = 0
        self.allsprites = pygame.sprite.Group()
        self.platforms = pygame.sprite.Group()
        self.fallingBlocks = pygame.sprite.Group()
        self.powerUps = pygame.sprite.Group()
        self.powerTimeMin, self.powerTimeMax = 200, 400
        self.powerUpInt = random.randint(self.powerTimeMin, self.powerTimeMax)
        self.enemies = pygame.sprite.Group()
        self.initGraphics()
        self.powerUpCounter = 0
        self.setPlatforms()
        self.setEnemies()
        self.setOptions()

    def setPlatforms(self):
        width, height = self.screenSize
        cx, cy = width/2, (height) - 100
        self.mainPlatform = mainPlatform = MainPlatform(cx, cy)
        self.platforms.add(mainPlatform)
        self.allsprites.add(mainPlatform)
        for pCx, pCy in self.platformsList:
            self.newPlatform(pCx, pCy)

    def setEnemies(self):
        for x, y in self.enemiesList:
            self.newFireball(x, y)

    def setOptions(self):
        if 'lockingPlatforms' in self.levelData:
            for pCx, pCy in self.levelData['lockingPlatforms']:
                self.newPlatform(pCx, pCy, LockingPlatform)
        if 'movingEnemies' in self.levelData:
            for x, y in self.levelData['movingEnemies']:
                self.newFireball(x, y, MovingFireball)

    def initGraphics(self):
        self.initPauseMenu()
        self.initLossMenu()
        self.initWinMenu()
        self.initScoreboard()
        self.loadBackground()
        self.consola_font = pygame.font.SysFont('consola.ttf', 20)

    def loadBackground(self):
        if 'background' in self.levelData:
            background = self.levelData['background']
        else: background = 'Backgrounds/defaultbackground.png'
        self.background, backgroundRect = load_image(background)

    # Set up menus for paused, failed level, and win modes:

    def initPauseMenu(self):
        self.pauseMenuSprites = pygame.sprite.Group()
        retry = Button(110, 300, 'Buttons/retry.png', 'retry')
        levelQuit = Button(340, 300, 'Buttons/quit.png', 'quit')
        self.pauseMenuSprites.add(retry, levelQuit)
        pauseImage, pauseRect = load_image('Backgrounds/pausesurface.png')
        self.pauseSurface = pauseImage
        self.pauseSurfacePos = (100, 150)

    def initLossMenu(self):
        self.lossMenuSprites = pygame.sprite.Group()
        retry = Button(110, 300, 'Buttons/retry.png', 'retry')
        levelQuit = Button(340, 300, 'Buttons/quit.png', 'quit')
        self.lossMenuSprites.add(retry, levelQuit)
        lossImage, lossRect = load_image('Backgrounds/oversurface.png')
        self.lossSurface = lossImage
        self.lossSurfacePos = (100, 150)

    def initWinMenu(self):
        self.winMenuSprites = pygame.sprite.Group()
        win = Button(110, 300, 'Buttons/nextlevel.png', 'nextLevel')
        levelQuit = Button(340, 300, 'Buttons/quit.png', 'quit')
        self.winMenuSprites.add(win, levelQuit)
        winImage, winRect = load_image('Backgrounds/winsurface.png')
        win1Image, win1Rect = load_image('Backgrounds/redwin.png')
        win2Image, win2Rect = load_image('Backgrounds/bluewin.png')
        drawImage, drawRect = load_image('Backgrounds/draw.png')
        self.winSurface = winImage
        self.win1Image, self.win2Image = win1Image, win2Image
        self.drawImage = drawImage
        self.winSurfacePos = (100, 150)

    def initScoreboard(self):
        self.scorePos = (50, 50)
        self.livesPos = (300, 50)
        self.blocksPos = (400, 50)

    def run(self, size, screen, clock, player = None):
        self.screenSize = width, height = size
        self.screen = screen
        self.clock = clock
        self.init()
        self.player = player
        self.placePlayer(width/2, height/2)
        while self.mode != False:
            if self.timerFired() == False:
                return False
            elif self.timerFired() == True:
                return self.player
            elif self.mode == 'Quit':
                return None
        return False

    def __init__(self, file = 'Levels/level'):
        self.levelData = data = shelve.open(file)
        requiredData = ['maxBlocks', 'platforms', 'dropSpace', 'enemies']
        for item in requiredData:
            if item not in self.levelData:
                print "Cannot load level:", file
                raise SystemExit
        self.maxBlocks = data['maxBlocks']
        self.platformsList = data['platforms']
        self.enemiesList = data['enemies']

class TwoPlayerLevel(GameLevel):

    # Edited some functions to accomodate a list of players

    # Controls

    def mousePressed(self, event):
        (x, y) = self.mousePos
        if self.mode == 'Pause':
            resume = True
            for button in self.pauseMenuSprites:
                if button.rect.collidepoint(x, y):
                    self.runButton(button.eventName)
                    resume = False
            if resume == True:
                self.mode = None
        elif self.mode == 'Over':
            # For now this is the same as win
            for button in self.winMenuSprites:
                if button.rect.collidepoint(x, y):
                    self.runButton(button.eventName)
        elif self.mode == 'Lost':
            for button in self.lossMenuSprites:
                if button.rect.collidepoint(x, y):
                    self.runButton(button.eventName)

    def retryLevel(self):
        width, height = self.screenSize
        self.mode = None # Unpauses
        self.player1 = None # Resets so that we can make a new player
        self.player2 = None
        self.init()
        self.placePlayers()

    def keyPressed(self, event):
        if event.key == pygame.K_p and self.mode == None:
            if self.mode != "Pause":
                self.mode = "Pause"
            else: self.mode = None
        if self.mode == None and self.player1 != None:
            self.playerOneControls(event)
        if self.mode == None and self.player2 != None:
            self.playerTwoControls(event)

    def playerOneControls(self, event):
        if event.key == pygame.K_RIGHT:
            self.player1.walk(1)
        elif event.key == pygame.K_LEFT:
            self.player1.walk(-1)
        elif event.key == pygame.K_UP:
            self.player1.jump()

    def playerTwoControls(self, event):
        if event.key == pygame.K_d:
            self.player2.walk(1)
        elif event.key == pygame.K_a:
            self.player2.walk(-1)
        elif event.key == pygame.K_w:
            self.player2.jump()

    # Game mechanics

    def handleCollisions(self):
        self.handlePlatformCollisions()
        self.enemyCollisions()
        self.newBlock()
        self.handlePowerUps()
        self.setPowerUps()
        self.adjustBlocks()
        self.clearOldSprites()
        for player in self.playersList:
            if player.lives == 0:
                if player == self.player1:
                    self.player2.score += 1
                else: self.player1.score += 1
                self.resetPlayer()
                self.mode = "Over"

    def resetPlayer(self):
        # Simle rest on both players
        self.player1.reset()
        self.player2.reset()

    def clearOldSprites(self):
        # Manages any sprites that go off-screen
        width, height = self.screenSize
        for sprite in self.allsprites:
            if (sprite.rect.top > height):
                if isinstance(sprite, Player):
                    sprite.loseLife(True)
                else:
                    sprite.kill()
            elif (sprite.rect.left < 0 or sprite.rect.right > width):
                if isinstance(sprite, Player):
                    sprite.rect.left = sprite.rect.left % width
                else:
                    sprite.kill()

    def setPowerUps(self):
        self.powerUpCounter += 1
        # Get rectangular limits of where powerups can be placed
        (x1, x2) = self.levelData['powerupsX']
        (y1, y2) = self.levelData['powerupsY']
        if len(self.powerUps) == 0 and self.powerUpCounter == self.powerUpInt:
            x = random.randint(x1, x2)
            y = random.randint(y1, y2)
            self.newPowerUp(x, y)
            self.powerUpCounter = 0
            # Decide how long to wait before next powerup spawns:
            wait = random.randint(self.powerTimeMin, self.powerTimeMax)
            self.powerUpInt = wait

    # Collisions and physics

    def handlePowerUps(self):
        power = None
        for powerup in self.powerUps:
            for player in self.playersList:
                if pygame.sprite.collide_rect(powerup, player):
                    player.reset()
                    player.power = power = powerup.power
                    updatePlayer = player
                powerup.kill()
        if power != None:
            self.applyPowerUp(updatePlayer, power)

    def applyPowerUp(self, player, power):
        if power == 'Heavy':
            player.changeWeight(2) # doubles player weight
        elif power == "Light":
            player.changeWeight(0.5) # halves player weight
        elif power == "Fast":
            player.speed *= 2
        elif power == "Slow":
            player.speed /= 2.0

    def handlePlatformCollisions(self):
        for platform in self.platforms:
            totalweight = 0
            for block in self.fallingBlocks:
                if self.isOnPlatform(block, platform):
                    totalweight += self.getBlockWeight(block, platform)
                    if block.onPlatform == False: # just landed
                        block.vy = 0
                        block.jumpStep = 0
                    block.onPlatform = True
            platform.adjustPlatformAngle(totalweight)
        for block in self.fallingBlocks:
            if self.platformsHit(block) == []:
                block.onPlatform = False

    def enemyCollisions(self):
        # Lose lives when hit by raindrops or by each other
        for player in self.playersList:
            hitList = pygame.sprite.spritecollide(player,
                self.fallingBlocks, False)
            for block in hitList:
                if not player.block and not isinstance(block, Player):
                    player.loseLife()

    def newBlock(self):
        width, height = self.screenSize
        blockLimit = 3
        if len(self.fallingBlocks) < blockLimit:
            if self.blockCounter == self.maxBlocks:
                self.mode = 'Over'
            else:
                x = self.getDropLocation()
                block = Raindrop(x,0)
                self.allsprites.add(block)
                self.fallingBlocks.add(block)
                self.blockCounter += 1
                self.currentBlock = block

    def placePlayers(self):
        (x1, y1) = self.levelData['Player1Pos']
        (x2, y2) = self.levelData['Player2Pos']
        self.player1 = self.placePlayer(x1, y1, 1, self.player1)
        self.player2 = self.placePlayer(x2, y2, 2, self.player2)

    def placePlayer(self, x, y, number, player):
        if player == None:
            player = Player(x, y, number)
        else:
            player.rect.left = x
            player.rect.top = y
            player.fullReset()
        self.allsprites.add(player)
        self.fallingBlocks.add(player)
        self.playersList.add(player)
        return player

    # Drawing

    def redrawAll(self):
        self.screen.blit(self.background, (0,0))
        self.drawScore()
        self.drawHealthBars()
        for sprite in self.allsprites:
            self.screen.blit(sprite.image, (sprite.rect.x, sprite.rect.y))
        if self.mode == 'Pause':
            self.screen.blit(self.pauseSurface, self.pauseSurfacePos)
            self.pauseMenuSprites.draw(self.screen)
        elif self.mode == 'Over':
            if self.player2.lives == 0:
                self.screen.blit(self.win1Image, self.winSurfacePos)
            elif self.player1.lives == 0:
                self.screen.blit(self.win2Image, self.winSurfacePos)
            else: self.screen.blit(self.drawImage, self.winSurfacePos)
            self.winMenuSprites.draw(self.screen)
        elif self.mode == 'Lost':
            self.screen.blit(self.lossSurface, self.lossSurfacePos)
            self.lossMenuSprites.draw(self.screen)
        pygame.display.flip()

    def drawHealthBars(self):
        for player in self.playersList:
            # Get position to blit health bar
            margin = 3
            (x, y) = player.rect.topleft
            (x, y) = (x - margin, y - margin)
            self.screen.blit(player.healthBar, (x, y))

    def drawScore(self):
        scoreColor = (46,139,87)
        score = "Score: %d - %d" % (self.player2.score, self.player1.score)
        lives = "Lives: %d - %d" % (self.player2.lives, self.player1.lives)
        blocks = self.maxBlocks - self.blockCounter
        blockText = "Drops remaining: %d/%d" % (blocks, self.maxBlocks)
        scoreDraw = self.consola_font.render(score, True, scoreColor)
        livesDraw = self.consola_font.render(lives, True, scoreColor)
        blocksDraw = self.consola_font.render(blockText, True, scoreColor)
        self.screen.blit(scoreDraw, self.scorePos)
        self.screen.blit(livesDraw, self.livesPos)
        self.screen.blit(blocksDraw, self.blocksPos)

    # Set up stuff

    def init(self):
        self.playersList = pygame.sprite.Group()
        super(TwoPlayerLevel, self).init()

    def initScoreboard(self):
        self.scorePos = (50, 50)
        self.livesPos = (300, 50)
        self.blocksPos = (400, 50)

    def run(self, size, screen, clock, p1 = None, p2 = None):
        self.screenSize = width, height = size
        self.screen = screen
        self.clock = clock
        self.init()
        self.player1 = p1
        self.player2 = p2
        self.placePlayers()
        while self.mode != False:
            if self.timerFired() == False:
                return False
            elif self.timerFired() == True:
                return self.player1, self.player2
            elif self.mode == 'Quit':
                return None
        return False
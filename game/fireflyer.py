import pygame
import random
from pygame.locals import *
import math
import shelve
import os
from Classes import *
from GlobalFunctions import *
from Level import *
from ComputerLevel import *

class Game(object):

    def mousePressed(self, event):
        (x, y) = self.mousePos
        if self.mode == None:
            for button in self.startMenuSprites:
                if button.rect.collidepoint(x, y):
                    self.runButton(button.eventName)
        elif self.mode == 'Instructions':
            for button in self.instructionsButtons:
                if button.rect.collidepoint(x, y):
                    self.runButton(button.eventName)

    def runButton(self, eventName):
        if eventName == '1p':
            self.mode = 1
        elif eventName == '2p':
            self.mode = 2
        elif eventName == 'instruct':
            self.mode = 'Instructions'
        # Back and forwards buttons should only be in instrutions
        elif eventName == 'back':
            if self.instructionsScreen > 0:
                self.instructionsScreen -= 1
        elif eventName == 'forwards':
            if self.instructionsScreen < self.maxScreen:
                self.instructionsScreen += 1
        elif eventName == 'return':
            self.mode = None
            self.instructionsScreen = 0

    def timerFired(self):
        self.redrawAll()
        self.mousePos = pygame.mouse.get_pos()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                self.mode = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.mousePressed(event)

    def redrawAll(self):
        self.screen.fill((255,255,255))
        if self.mode == "Instructions":
            instructions = self.instructions[self.instructionsScreen]
            self.screen.blit(instructions, (0,0))
            self.instructionsButtons.draw(self.screen)
        else:
            self.screen.blit(self.background, (0,0))
            self.startMenuSprites.draw(self.screen)
        pygame.display.flip()

    def init(self):
        self.mode = None
        self.player = None
        self.player2 = None
        self.makeLevels()
        self.initStartScreen()
        self.initInstructions()
        self.currentLevel = 0
        self.current2p = 0

    def initStartScreen(self):
        # Background image from http://www.graphic-cauldron.blogspot.it/
        self.startMenuSprites = pygame.sprite.Group()
        background, bgRect = load_image("Backgrounds/background.png")
        self.background = pygame.transform.scale(background, self.screenSize)
        onePlayer = Button(100, 400, 'Buttons/oneplayer.png', '1p')
        twoPlayer = Button(330, 400, 'Buttons/twoplayer.png', '2p')
        instructions = Button(400, 550, 'Buttons/instructions.png', 'instruct')
        self.startMenuSprites.add(onePlayer, twoPlayer, instructions)

    def initInstructions(self):
        # Arrow key images: http://vector.me/browse/215565/arrow_keys_vectors
        # WASD key images: http://www.shutterstock.com/pic.mhtml?id=143474011
        self.instructionsScreen = 0
        self.maxScreen = 2
        self.instructionsButtons = pygame.sprite.Group()
        instruction, instructsRect = load_image("Backgrounds/instructions.png")
        onePlayer, onePlayerRect = load_image("Backgrounds/instructions1.png")
        twoPlayer, twoPlayerRect = load_image("Backgrounds/instructions2.png")
        self.instructions = [instruction, onePlayer, twoPlayer]
        back = Button(50, 50, 'Buttons/back.png', 'back')
        forwards = Button(500, 50, 'Buttons/forward.png', 'forwards')
        goBack = Button(3, 3, 'Buttons/return.png', 'return')
        self.instructionsButtons.add(back, forwards, goBack)

    def makeLevels(self):
        # All the same level for now.
        # Just to test ability to switch between them
        enemies2 = [(400, 400)]
        level1 = GameLevel('Levels/level1')
        level2 = GameLevel('Levels/level2')
        level3 = GameLevel('Levels/level3')
        BossLevel = ComputerLevel('Levels/level2p1')
        level2p2 = TwoPlayerLevel('Levels/level2p1')
        self.levels = [level1, level2, level3, BossLevel]
        self.levels2p = [level2p2]

    def playLevel(self):
        level = self.levels[self.currentLevel]
        result = level.run(self.screenSize, self.screen, self.clock,
            self.player)
        if result == False: # Exited game
            self.mode = False
        elif result == None: # Quit to main menu, reset the round
            self.resetLevels()
        else:
            # player object stores lives/score, and successful level returns
            # the player
            self.player = result
            self.currentLevel += 1

    def play2pLevel(self):
        level = self.levels2p[self.current2p]
        result = level.run(self.screenSize, self.screen, self.clock,
            self.player, self.player2)
        if result == False: # Exited game
            self.mode = False
        elif result == None: # Quit to main menu, reset the round
            self.resetLevels()
        else:
            # Successful level returns the player
            self.player, self.player2 = result
            self.currentLevel += 1

    def resetLevels(self):
        self.mode = None
        self.currentLevel = 0
        self.current2p = 0
        self.player = None
        self.player2 = None
        self.makeLevels()

    def run(self, width = 600, height = 600):
        pygame.init()
        self.screenSize = (width, height)
        self.screen = pygame.display.set_mode(self.screenSize)
        pygame.display.set_caption("Fire Flyer")
        self.clock = pygame.time.Clock()
        self.init()
        while self.mode != False:
            if self.mode == 1: # Currently playing
                if self.currentLevel == len(self.levels):
                    self.resetLevels()
                else: self.playLevel()
            if self.mode == 2:
                if self.currentLevel == len(self.levels2p):
                    self.resetLevels()
                else: self.play2pLevel()
            else:
                self.timerFired()
        pygame.quit()

Game().run()

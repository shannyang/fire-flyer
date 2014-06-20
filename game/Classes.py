import pygame
import random
from pygame.locals import *
from GlobalFunctions import *
import math

class Button(pygame.sprite.Sprite):
    def __init__(self, x, y, imagePath, eventName):
        super(Button, self).__init__()
        self.image, self.rect = load_image(imagePath, -1)
        self.rect.left = x
        self.rect.top = y
        self.eventName = eventName


############################
# Physics objects for game
############################

class GravityObject(pygame.sprite.Sprite):

    # Root class for raindrop, firedrop, and players.

    def __init__(self, x, y):
        super(GravityObject, self).__init__()
        self.onPlatform = False
        self.image, self.rect = load_image('Sprites/raindrop.png', -1)
        # store an unrotated image to keep graphics clean
        self.original = self.image
        self.rect.left = x
        self.rect.top = y
        self.jumpStep = 0
        self.speed = 1 # For "speed-up" powerups, a multiplier on velocity
        self.vx = self.vy = 0
        self.terminalVelocity = 15
        self.weight = 0.5
        self.angle = self.targetAngle = 0

    def rotate(self):
        if self.targetAngle != 0:
            self.angle += self.targetAngle
            self.image = pygame.transform.rotate(self.original, self.angle)

    def adjustRect(self):
        # Because size/rotation changes should cause rects to change as well
        x, y = self.rect.left, self.rect.top
        self.rect = self.image.get_rect()
        self.rect.left = x
        self.rect.top = y

    def update(self):
        self.rotate()
        self.adjustRect()
        self.rect.x += self.vx*self.speed
        self.vx *= 0.95
        self.rect.y += self.vy
        if not self.onPlatform and self.vy < self.terminalVelocity:
            self.vy += 1

class Raindrop(GravityObject):

    def __init__(self, x, y):
        super(Raindrop, self).__init__(x, y)
        self.sideways = pygame.transform.rotate(self.original, 90)
        self.dropType = 1 # indicates a normal raindrop

    def rotate(self):
        if self.onPlatform:
            image = self.sideways
            if self.vx < 0:
                image = pygame.transform.flip(image, True, False)
        else: image = self.original
        if self.targetAngle != 0:
            self.angle += self.targetAngle
            self.image = pygame.transform.rotate(image, self.angle)

class Firedrop(Raindrop):

    # For use in boss level!

    def __init__(self, x, y):
        super(Firedrop, self).__init__(x, y)
        self.image, self.rect = load_image('Sprites/firedrop.png', -1)
        self.original = self.image
        self.sideways = pygame.transform.rotate(self.original, 90)
        self.rect.left = x
        self.rect.top = y
        self.dropType = 2 # this drop will injure user-controlled players

class Player(GravityObject):

    def __init__(self, x, y, number = 1, lives = 3):
        super(Player, self).__init__(x, y)
        self.initX, self.initY = x, y
        self.lives = self.maxlives = lives
        self.jumpHeight = 10
        self.dx = 1 # Tracks direction the player last walked in
        self.score = 0
        self.block = False
        self.blockTimer = 0
        # Store score data in player - to transition between levels
        self.initImage(number)
        self.rect.left = x
        self.rect.top = y
        self.updateHealthBar()
        self.reset()

    def initImage(self, number):
        # permCopy = kept for fully resetting the image
        # original = same direction/size as sprite, but unrotated
        imageName = 'Sprites/player%d.png' % number
        hitImageName = 'Sprites/player%dhit.png' % number
        self.image, self.rect = load_image(imageName, -1)
        # discard the hitrect and permrect
        self.hitImage, hitrect = load_image(hitImageName, -1)
        self.permCopy, permRect = load_image(imageName, -1)
        self.original = self.image

    def changeWeight(self, weightChange):
        # Reacts to weight-change powerups
        if weightChange > 1:
            newSize = (30, 30)
        else:
            newSize = (10, 10)
        self.weight = int(self.weight*weightChange)
        image = pygame.transform.scale(self.image, newSize)
        self.image = self.original = image

    def loseLife(self, respawn = False):
        # respawn = Boolean (whether to reset to first position)
        if not self.block:
            self.lives -= 1
            self.block = True
            self.updateHealthBar()
            if respawn:
                self.rect.left = self.initX
                self.rect.top = self.initY
                self.fullReset()
            else: self.reset()
            self.image = self.original = self.hitImage

    def updateBlock(self):
        if self.block:
            self.blockTimer += 1
        if self.blockTimer == 20:
            self.blockTimer = 0
            self.block = False
            self.reset() # to get rid of the hit image

    def reset(self):
        # Changes powerup properties back to normal
        image = self.permCopy
        if self.dx == -1:
            image = pygame.transform.flip(image, True, False)
        self.image = self.original = image
        self.speed = 1
        self.weight = 2
        self.power = None
        self.powerTimer = 0

    def fullReset(self):
        # Additional resetting to get rid of movement at level's end
        self.reset()
        self.vx = 0
        self.vy = 0

    def updatePowers(self):
        # Removes powerups after 200 frames
        if self.power != None:
            self.powerTimer += 1
        if self.powerTimer == 200:
            self.reset()

    def update(self):
        super(Player, self).update()
        self.updateBlock()
        self.updatePowers()
        if self.vy > self.jumpHeight:
            # jump has ended (actually need to calibrate this thing, but oh well)
            self.jumpStep = 0

    def walk(self, dx):
        if self.dx != dx:
            self.image = pygame.transform.flip(self.original, True, False)
            self.vx = 5*dx
            self.angle = 0
            self.original = self.image
        else:
            self.vx += 3*dx
            self.rect.x += self.vx
        self.dx = dx

    def jump(self):
        if self.jumpStep < 2:
        # Later - check that player is on platform, or has just left one?
        # Want to prevent more than 2 consecutive jumps
            self.vy -= self.jumpHeight
            self.jumpStep += 1

    def updateHealthBar(self): # Called whenever player loses a life
        # Calculate filled area
        fullBarSize = 20.0
        barHeight = 3
        healthColor = (255,0,0)
        currentHealth = (self.lives)*(fullBarSize/self.maxlives)
        imageSize = (int(fullBarSize), int(barHeight))
        filledAreaSize = (int(currentHealth), int(barHeight))
        # Create healthBar and currentHealth images, then blit currentHealth
        healthBar = pygame.Surface(imageSize).convert_alpha()
        currentHealthBar = pygame.Surface(filledAreaSize).convert_alpha()
        currentHealthBar.fill(healthColor)
        healthBar.blit(currentHealthBar, (0,0))
        self.healthBar = healthBar

class Platform(pygame.sprite.Sprite):

    def __init__(self, cx, cy, resistance = 0, height = 15, width = 200):
        super(Platform, self).__init__()
        self.width, self.height = width, height
        # Platform images by alhovik
        # http://www.123rf.com/photo_11196023_seamless-roof-tiles.html
        self.image, self.rect = load_image('Sprites/platform.png', -1)
        self.original = self.image
        (self.cx, self.cy) = cx, cy
        (self.rect.x, self.rect.y) = (cx-width/2, cy-height/2)
        self.resistance = resistance
        self.angle = 0
        self.targetAngle = 0 # platform rotates by this much at next frame
        self.maxAngle = 60

    def adjustPlatformAngle(self, weight):
        if abs(weight) > abs(self.angle):
            # Rotate downwards
            self.targetAngle = (weight/14.0)*(1-self.resistance)
        elif abs(weight) < abs(self.angle):
            # Rotate back to flat angle
            self.targetAngle = -(self.angle/7.0)

    def rotate(self):
        if abs(self.angle + self.targetAngle) < self.maxAngle:
            self.angle += self.targetAngle
            self.image = pygame.transform.rotate(self.original, self.angle)
            self.rect = self.image.get_rect()
            self.rect.center = (self.cx, self.cy)

    def update(self):
        self.rotate()

class LockingPlatform(Platform):

    # Once pushed down in one direction, it can only rotate in that direction
    
    def __init__(self, cx, cy, resistance = 0, height = 15, width = 200):
        super(LockingPlatform, self).__init__(cx, cy, resistance, height,
            width)
        self.maxAngle = 45
        self.image, self.rect = load_image('Sprites/lockplatform.png', -1)
        self.original = self.image
        (self.rect.x, self.rect.y) = (cx-self.width/2, cy-self.height/2)

    def rotate(self):
        if self.canRotate():
            super(LockingPlatform, self).rotate()

    def canRotate(self):
        # Locking platforms cannot rotate back toward an angle of 0
        # Check whether the increment has the same sign as the current angle
        if self.angle == 0 or self.targetAngle == 0:
            return True
        else:
            currentAngleSign = abs(self.angle)/self.angle
            incrementSign = abs(self.targetAngle)/self.targetAngle
            return currentAngleSign == incrementSign

class MainPlatform(Platform):

    # Just a big platform at the bottom of the screen

    def __init__(self, cx, cy):
        resistance = 0.8
        super(MainPlatform, self).__init__(cx, cy, resistance, 30, 400)
        self.image, self.rect = load_image('Sprites/mainplatformimg.png', -1)
        self.original = self.image
        (self.rect.x, self.rect.y) = (cx-self.width/2, cy-self.height/2)


class PowerUp(pygame.sprite.Sprite):

    # Each time a powerup is made, choose its attributes randomly

    powerUps = ['Heavy', 'Light', 'Fast']

    heavy = 'Sprites/heavypower.png'
    light = 'Sprites/lightpower.png'
    fast = 'Sprites/fastpower.png'
    powerUpImgs = [heavy, light, fast]

    def __init__(self, x, y):
        super(PowerUp, self).__init__()
        choice = random.randint(0,2)
        self.power = PowerUp.powerUps[choice]
        image = PowerUp.powerUpImgs[choice]
        self.image, self.rect = load_image(image)
        self.image = self.image.convert_alpha()
        self.original = self.image
        self.rect.left = x
        self.rect.top = y
        self.time = 0
        self.maxTime = 150 # number of frames it lasts for

    def update(self):
        if self.time >= self.maxTime:
            self.kill()
        else:
            self.time += 1
            rotate = 4*self.time
            oldCenter = self.rect.center
            self.image = pygame.transform.rotate(self.original, rotate)
            self.rect = self.image.get_rect()
            self.rect.center = oldCenter

class Fireball(pygame.sprite.Sprite):

    # Images change depending on how many lives are left
    # All are adapted from: www.norbertbayer.de/
    life3 = 'Sprites/fireball3lives.png'
    life2 = 'Sprites/fireball2lives.png'
    life1 = 'Sprites/fireball1life.png'
    fireballImgs = [life1, life2, life3]

    def __init__(self, x, y, lives):
        super(Fireball, self).__init__()
        self.lives = self.maxlives = lives
        self.image, self.rect = load_image(Fireball.fireballImgs[lives-1], -1)
        self.original = self.image
        self.rect.left = self.x = x
        self.rect.top = self.y = y
        self.block = False # "blocks" for a while after collision
        self.blockTimer = 0
        self.maxBlockTime = 15
        self.angle = self.targetAngle = 0

    def loseLife(self):
        if not self.block:
            self.lives -= 1
            self.block = True
            if self.lives > 0:
                newImage = Fireball.fireballImgs[self.lives-1]
                self.image, self.rect = load_image(newImage, -1)
                self.rect.left = self.x
                self.rect.top = self.y

    def update(self):
        # block prevents fireball from losing multiple lives from one hit
        if self.block:
            self.blockTimer += 1
        if self.blockTimer == self.maxBlockTime:
            self.blockTimer = 0
            self.block = False

class MovingFireball(Fireball):

    def __init__(self, x, y, lives):
        super(MovingFireball, self).__init__(x, y, lives)
        self.maxDistance = 30
        self.vx = -4

    def update(self):
        super(MovingFireball, self).update()
        if not self.block:
            # Moves within some distance of starting position
            distance = abs(self.x - self.rect.left)
            if distance > self.maxDistance:
                self.vx *= -1
            self.rect.left += self.vx

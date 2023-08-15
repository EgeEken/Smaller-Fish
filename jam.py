import pygame as pg
import time
from levels import levellist, Fish, Gun, Button

pg.init()
LEVELLIST = levellist
FONT = pg.font.SysFont("comicsans", 15)


class Game:
    def __init__(self, levels=LEVELLIST, fps=60):

        self.screen = None

        self.clock = pg.time.Clock()
        self.fps = fps

        self.levels = levels
        self.level = 0  # current level index

    def render(self):
        self.screen.fill((255, 255, 255))
        w, h = self.screen.get_size()
        pg.draw.rect(self.screen, (0, 0, 180),
                     (0, self.levels[self.level].waterlevel, w, h - self.levels[self.level].waterlevel))
        for wall in self.levels[self.level].walls:
            pg.draw.rect(self.screen, wall.color, wall.pg_rect)
        for obj in self.levels[self.level].objects:
            
            if isinstance(obj, Button) and not obj.pressed:
                pg.draw.rect(self.screen, obj.color, obj.pg_rect)
                
            elif isinstance(obj, Fish) and obj.alive:
                if obj.sprite is not None:
                    if obj.v.x < -0.5:
                        obj.sprite = obj.flippedsprites[obj.spriteindex]
                    elif obj.v.x > 0.5:
                        obj.sprite = obj.sprites[obj.spriteindex]
                    self.screen.blit(obj.sprite, obj.topleft)
                else:
                    pg.draw.rect(self.screen, obj.color, obj.pg_rect)

                
            elif isinstance(obj, Gun) and not obj.picked:
                if obj.sprite is not None:
                    self.screen.blit(obj.sprite, obj.topleft)
                else:
                    pg.draw.rect(self.screen, obj.color, obj.pg_rect)

        if self.levels[self.level].player.image is not None:
            if self.levels[self.level].player.v.x <= 0:
                self.screen.blit(self.levels[self.level].player.flipped, self.levels[self.level].player.topleft)
            else:
                self.screen.blit(self.levels[self.level].player.image, self.levels[self.level].player.topleft)
        else:
            pg.draw.rect(self.screen, self.levels[self.level].player.color, self.levels[self.level].player.pg_rect)

        if self.levels[self.level].player.ray_start is not None:
            pg.draw.line(self.screen, (255, 0, 0),
                         self.levels[self.level].player.ray_start, self.levels[self.level].player.ray_end, width=10)
        o2 = int(self.levels[self.level].player.oxygen // 100)
        if o2 < 10:
            oxygen = FONT.render(f"Oxygen: {int(self.levels[self.level].player.oxygen // 100)}", True, (255, 0, 0))
            self.screen.blit(oxygen, (self.levels[self.level].player.topleft.x - 20, self.levels[self.level].player.topleft.y - 40))
        if self.levels[self.level].text is not None:
            self.screen.blit(self.levels[self.level].text, self.levels[self.level].textpos)
        pg.display.flip()
        pg.display.update()


def main():
    dt = 0
    game = Game()
    while len(game.levels) > game.level:
        game.screen = pg.display.set_mode((game.levels[game.level].screenwidth, game.levels[game.level].screenheight))
        game.levels[game.level].reset()
        while game.levels[game.level].cleared == False and game.levels[game.level].player.alive == True:
            # delta time
            game.levels[game.level].update(dt)
            game.render()
            dt = game.clock.tick(game.fps) / 1000
        if game.levels[game.level].player.alive == False:
            print("You died!")
        else:
            print("Level clear!")
            game.level += 1
    win = pg.image.load("win.png")
    game.screen.blit(win, (0, 0))
    pg.display.flip()
    pg.display.update()
    time.sleep(1)
    print("You win!")
    pg.quit()


if __name__ == "__main__":
    main()

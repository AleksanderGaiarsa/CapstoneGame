import pygame
import random
import pygame_gui
import modules.game_objects as g_obj
import modules.gui as gui
import modules.game_algos as algo
import modules.calibration as calib
import modules.joycon as joycon
import modules.ml_output as mach_learn
import queue
import time
from decimal import Decimal, ROUND_UP
import asyncio


class Shooting_Game():
    def __init__(self, bullet_rate_idx, q_to_ble, q_from_ble, calibration:calib.Calibration, Calibration_flag=False):

        pygame.mixer.music.load('./Game/assets/Stone_Cold.mp3',)
        pygame.mixer.music.play(100, fade_ms=1000)

        self.calib_flag = Calibration_flag
        self.calibration = calibration

        #ML
        self.calibration.calib_data()
        self.ml_output = mach_learn.Outputs()
        self.gsr_val = 500

        if self.calib_flag:
            with open('./Game/references/Calibration.csv', 'w') as f:
                f.write('Time,Bullet Speed,GSR\n')

        #GUI
        if self.calib_flag:
            self.dmg_factor = 4
        else:
            self.dmg_factor = 20

        pygame.display.set_caption("Game Simulation")
        self.display = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
        self.disp_w, self.disp_h = pygame.display.get_surface().get_size()
        self.fps = 60

        self.gui = gui.GUI(self.disp_w, self.disp_h, self.calibration)
        self.font = self.get_font(26)

        if self.calib_flag:
            self.bullet_rate_idx = 1
        else:
            self.bullet_rate_idx = bullet_rate_idx
            self.gui.lvl_diff.selected_option = self.gui.diff_list[self.bullet_rate_idx]

        self.q_to_ble = q_to_ble
        self.q_from_ble = q_from_ble

        #Controls
        self.controller = joycon.Controller()

        self.background = pygame.Surface((self.disp_w, self.disp_h))
        self.background.fill((255,255,255), (0, 0, self.disp_w/6, self.disp_h)) #white background
        self.background.fill((0,0,0), (self.disp_w/6, 0, 4, self.disp_h)) #black line 
        self.background.fill((200,104,65), (self.disp_w/6+4, 0, self.disp_w, self.disp_h)) #orange background

        self.clock = pygame.time.Clock()
        self.timer1 = 1000
        self.deltat = 0

        #Game Objects
        self.player = g_obj.Player(800,500, size=3, png_image="./Game/assets/player.png")
        self.enemy = [  g_obj.Enemy(800,150, size=2, png_image="./Game/assets/enemy.png"),
                        g_obj.Enemy(500,790, size=2, png_image="./Game/assets/enemy.png"),
                        g_obj.Enemy(1200,150, size=2, png_image="./Game/assets/enemy.png"),
                        g_obj.Enemy(1300,750, size=2, png_image="./Game/assets/enemy.png"),
                        g_obj.Enemy(380,320, size=2, png_image="./Game/assets/enemy.png"),
                        ]
        self.bullet_rate = [1000, 500, 250, 100] #Bullet fired every X milliseconds

        #Score
        self.score_interval = 30*(4-self.bullet_rate_idx) # every 1 to 5 seconds based
        self.score_event = pygame.USEREVENT + 1
        pygame.time.set_timer(self.score_event, self.score_interval)
        self.score = 0
        
        #Start Game
        self.run = True

        self.play()

    def get_font(self, size): # Returns Press-Start-2P in the desired size
        return pygame.font.Font("./Game/assets/font.ttf", size)

    def timer(self):
        self.timer1 -= self.deltat
        
        if self.timer1 <= 0:  # Ready to fire.
            counter = random.randint(0,4)
            self.enemy[counter].bullets.append(g_obj.Bullets(self.display, self.enemy[counter].x, self.enemy[counter].y, 
                                                            self.player.x, self.player.y, self.gui.slider_value))
            self.timer1 = self.bullet_rate[self.bullet_rate_idx]  # Reset the timer.
            
        self.deltat = self.clock.tick(self.fps) #milliseconds
    
    def pygame_event_check(self):

        for event in pygame.event.get():

            if event.type == pygame.QUIT:
                self.run = False
            
            elif event.type == pygame_gui.UI_HORIZONTAL_SLIDER_MOVED:
                if event.ui_element == self.gui.speed_slider:
                    self.gui.slider_value = event.value
            
            elif event.type == pygame.USEREVENT+3:
                if not self.calib_flag:
                    self.player.sword.swing(self.player.x+20, self.player.y+5)
            
            elif event.type == self.score_event:
                self.score += 1
                    
            elif event.type == pygame.KEYDOWN: 
                if event.key == pygame.K_a:
                    self.player.x -= self.gui.movement_speed
                
                elif event.key == pygame.K_d:
                    self.player.x += self.gui.movement_speed
                
                elif event.key == pygame.K_w:
                    self.player.y -= self.gui.movement_speed
                
                elif event.key == pygame.K_s:
                    self.player.y += self.gui.movement_speed

                elif event.key == pygame.K_ESCAPE:
                    self.controller.run = False
                    self.run = False  # Set running to False to end the while loop.
        
            if event.type != pygame.USEREVENT+1: 
                self.gui.manager.process_events(event)
    
    def check_for_collisions(self):
        for enemy in self.enemy:
            for bullet in enemy.bullets:
                if self.player.sword.swinging:
                    if bullet.check_sword_collide(self.player.sword):
                        self.player.sword.swinging  = False
                elif bullet.check_player_collide(self.player, self.q_to_ble, self.ml_output.pwm):
                    enemy.bullets.remove(bullet)
                    self.player.damage(self.gui.slider_value*self.dmg_factor)
                    if self.player.current_health <= 0:
                        self.run = False

                bullet.draw(self.display)
    
    def draw(self):
        self.player.draw(self.display)
        self.player.sword.draw(self.display, x=self.player.x+20, y=self.player.y+5)
        self.player.health_bar.draw(self.display, self.player.current_health)

        for enemy in self.enemy:
            enemy.draw(self.display)
    
    def check_keys(self):
        global atot_index

        keys = pygame.key.get_pressed()

        if keys[pygame.K_a]:
            self.player.x -= self.gui.movement_speed
        if keys[pygame.K_d]:
            self.player.x += self.gui.movement_speed
        if keys[pygame.K_w]:
            self.player.y -= self.gui.movement_speed
        if keys[pygame.K_s]:
            self.player.y += self.gui.movement_speed
    
    def screen_update(self):
        pygame.display.update()

        #TODO
        health_score = int(((self.player.current_health/self.player.health_bar.health_ratio)/self.player.health_bar.health_bar_length*100))
        health_percent_txt = self.font.render(str(health_score)+'%', False, (0, 0, 0))

        label_score = self.font.render('Score:', False, (0, 0, 0))
        socre_txt = ("%06d" % (self.score,))
        score_txt = self.font.render(str(socre_txt), False, (0, 0, 0))
        
        self.display.blit(self.background, (0, 0))
        self.display.blit(health_percent_txt, (950,25))
        if not self.calib_flag:
            self.display.blit(label_score, (1100, 25))
            self.display.blit(score_txt, (1260, 25))

        self.gui.manager.draw_ui(self.display)
        self.gui.manager.update(self.deltat_s)

    def calibration_timer(self):

        if self.calib_flag:
            self.calib_now = Decimal(str(time.time())).quantize(Decimal('.1'), rounding=ROUND_UP) - self.calib_start_time
            if (self.calib_now%5 == 0) & (self.calib_timer_once == False) & (self.calib_now != 0):
                self.gui.slider_value += 2
                self.calib_timer_once = True
            elif self.prev_calib_time != self.calib_now:
                self.calib_timer_once = False
            elif self.calib_now >= self.calib_end_time:
                self.run = False

            self.prev_calib_time = self.calib_now

    
    def gsr_processing(self):

        self.q_to_ble.put({'Command':'read', 'Service':'GSR', 'Characteristic':'GSR Measurement', 'Value':0})

        while(not self.q_from_ble.empty()):
            gsr = self.q_from_ble.get()
            if self.calib_flag:
                if (gsr < 1010) & (gsr > 10):
                    with open('./Game/references/Calibration.csv', 'a') as f:
                        f.write(str(0)+','+str(self.gui.slider_value*5)+','+str(gsr)+'\n')  
                        pass
            else:
                if (gsr < 1010) & (gsr > 10):
                    self.gsr_val = gsr
        
        if not self.calib_flag:
            self.ml_output.predict_stress(self.gsr_val, self.calibration)
            self.ml_output.outputs()

            self.gui.slider_value = (int(self.ml_output.predicted_stress)/5)+1
            self.gui.speed_label.set_text("<font color='#FFFFFF'  size=4>"
                                          "Bullet Speed:"+str(self.gui.slider_value*5)+ " Km/h")
            
            self.gui.heart_rate_label.set_text("<font color='#FFFFFF' size=2>"
                                                "Heart Rate: <br>"
                                                "<font size=3>"
                                                "      "+str(self.ml_output.predicted_hr)+" bpm",)
            
            #self.gui.speed_label.set_text("<font color='#FFFFFF'  size=2>"
                                        #"Bullet Speed:"+str(self.gui.slider_value*5)+ " Km/h")
            #self.gui.movement_speed = algo.calculate_player_speed(self.calibration.current_heart, self.calibration.hr_rest)
        
    def play(self):
        #Setup
        
        if self.calib_flag:
            self.calib_end_time = 30
            self.calib_start_time = round(time.time())
            self.prev_calib_time = Decimal(str(time.time())).quantize(Decimal('.1'), rounding=ROUND_UP)- self.calib_start_time
            self.calib_timer_once = False
        
        while(self.run):

            self.gsr_processing()

            self.calibration_timer()
            
            self.deltat_s = self.deltat/1000 #seconds
            
            self.check_keys()
            
            self.draw()

            self.check_for_collisions()
            
            self.timer()

            self.screen_update()
            
            self.pygame_event_check()

            time.sleep(0.03)
        
        self.controller.run = False

        pygame.display.quit()
        

    
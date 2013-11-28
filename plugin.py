###
# Copyright (c) 2013, Artho van de Velde
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
###

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
import Math
import re
import MySQLdb as mdb
from urllib2 import urlopen
from bs4 import BeautifulSoup as BS, SoupStrainer as SS
from dbinfo import *

class Pokemon(callbacks.Plugin):
    """This module is for various Pokemon info. It retrieves data from
    a MySQL-database and Bulbapedia.
    """
    
    def _db(self, poke, querytype):
        try:
            con = mdb.connect(dbip, dbuser, dbpass, dbname)
            cur = con.cursor()
            if querytype == "poke":
                cur.execute("SELECT * FROM pokemon WHERE Name='%s'" % poke)
            if querytype == "evos":
                cur.execute("SELECT * FROM pokemon WHERE EvoFrom=(SELECT ID FROM pokemon WHERE Name='%s')" % poke)
            if querytype == "mega":
                cur.execute("SELECT * FROM megas WHERE PokeID=(SELECT ID FROM pokemon WHERE Name='%s')" % poke)
            if querytype == "X" or querytype == "Y":
                cur.execute("SELECT * FROM megas WHERE Form='%s' AND PokeID=(SELECT ID FROM pokemon WHERE Name='%s')" % (querytype, poke))
            if querytype == "forme":
                cur.execute("SELECT * FROM formes WHERE Forme='%s'" % poke)
            if querytype == "TEST":
                cur.execute("" % poke)
            return cur.fetchall()
        except mdb.Error, e:
            return 0
        finally:
            if con:
                con.close()
    
    def mega(self, irc, msg, args, poke):
        """<pokemon>
        
        Replies if the pokemon has a Mega evolution and if it has, the
        stats for it.
        """
        #To be built: Location of the Megastone.
        data = self._db(poke, "mega")
        if data:
            for i in data:
                msg = 'Mega ' + poke + ' '
                if i[2]:
                    msg += i[2] + ' '
                msg += '- Type: ' + i[3] 
                if i[4]:
                    msg += '/' + i[4]
                msg2 = "Stats - HP: " + str(i[5]) + " Atk: " + str(i[6]) + " Def: " + str(i[7]) + \
                    " Sp.Atk: " + str(i[8]) + " Sp.Def: " + str(i[9]) + " Spd: " + str(i[10])
                irc.reply(msg)
                irc.reply(msg2)
        else:
            irc.reply("Pokemon has no Megavolve.")
    
    mega = wrap(mega, ['something'])
    
    def ivsingle(self, irc, msg, args, poke, stat, amount, level, nature):
        """<[forme] pokemon> <stat> <amount> <level> <nature>
        
        Calculates the IV of a stat with given pokemon/level/nature.
        EVs are calculated as 0. Stat is "HP/ATK/DEF/STK/SDF/SPD".
        If pokemon has a forme (like Mega), capture it like "Mega Charizard X"
        or "Trash Wormadam" (plant is default).
        """
        poke = poke.split(' ')
        formes = ['SANDY', 'TRASH', 'SUNNY', 'RAINY', 'SNOWY', 'ATTACK', \
                  'DEFENSE', 'SPEED', 'SUNSHINE', 'HEAT', 'WASH', 'FROST', \
                  'FAN', 'MOW', 'ORIGIN', 'SKY', 'ZEN', 'THERIAN', 'BLACK', \
                  'WHITE', 'PIROUETTE', 'BLADE', 'AVERAGE', 'LARGE', 'SUPER']
        if str.upper(poke[0]) == 'MEGA':
            if len(poke) > 2:
                stats = self._db(poke, str.upper(poke[2]))
            else:
                stats = self._db(poke, 'mega')
        elif str.upper(poke[0]) in formes:
            stats = self._db(poke[0], 'forme')
        else:
            stats = self._db(poke, )
        irc.reply(str(stats))
        
        
    ivsingle = wrap(ivsingle, [optional('something'), 'something', 'something', 'int', 'int', 'something'])
    
    def iv(self, irc, msg, args, species, level, nature, hp, atk, defe, spa, spd, spe):
        """ <pokemon> <level> <nature> <hp> <atk> <def> <sp.atk> <sp.def> <spd>
        
        Calculates possible IVs of a given pokemon. Please insert all stats.
        """
        ####DOES NOT WORK - DEVELOPMENT NEEDED (rewrite to SQL request instead of file)
        ####!!!!!
        bases = []
 
        try:
            stats = [int(hp), int(atk), int(defe), int(spa), int(spd), int(spe)]
        except:
            irc.reply("Invalid argument(s)")
            return 0
 
        coefc = 0
        intercs = 0
        found = 0
        natures = 0
        high = []
        low = []
 
        naturre = str.upper(nature)
 
        if naturre == "SERIOUS" or naturre == "QUIRKY" or naturre == "HARDY" or naturre == "BASHFUL":
            natures = [0,1,1,1,1,1]
        elif naturre == "LONELY":
            natures = [0,1.1,0.9,1,1,1]
        elif naturre == "ADAMANT":
            natures = [0,1.1,1,0.9,1,1]
        elif naturre == "NAUGHTY":
            natures = [0,1.1,1,1,0.9,1]
        elif naturre == "BRAVE":
            natures = [0,1.1,1,1,1,0.9]
        elif naturre == "BOLD":
            natures = [0,0.9,1.1,1,1,1]
        elif naturre == "IMPISH":
            natures = [0,1,1.1,0.9,1,1]
        elif naturre == "LAX":
            natures = [0,1,1.1,1,0.9,1]
        elif naturre == "RELAXED":
            natures = [0,1,1.1,1,1,0.9]
        elif naturre == "MODEST":
            natures = [0,0.9,1,1.1,1,1]
        elif naturre == "MILD":
            natures = [0,1,0.9,1.1,1,1]
        elif naturre == "RASH":
            natures = [0,1,1,1.1,0.9,1]
        elif naturre == "QUIET":
            natures = [0,1,1,1.1,1,0.9]
        elif naturre == "CALM":
            natures = [0,0.9,1,1,1.1,1]
        elif naturre == "GENTLE":
            natures = [0,1,0.9,1,1.1,1]
        elif naturre == "CAREFUL":
            natures = [0,1,1,0.9,1.1,1]
        elif naturre == "SASSY":
            natures = [0,1,1,1,1.1,0.9]
        elif naturre == "TIMID":
            natures = [0,0.9,1,1,1,1.1]
        elif naturre == "HASTY":
            natures = [0,1,0.9,1,1,1.1]
        elif naturre == "JOLLY":
            natures = [0,1,1,0.9,1,1.1]
        elif naturre == "NAIVE":
            natures = [0,1,1,1,0.9,1.1]
        else:
            natures = [0,1,1,1,1,1]
   
        pokedb = open('local.txt', 'r')
 
        for i in pokedb.readlines():
            if i[0:len(species)] == species:
                found = 1
                index = 0
                sstring = ""
                for j in i:
                    if index != 0 and j != "|" and j != "\n":
                        sstring += j
                    if j == "|":
                        index += 1
                        bases.append(int(sstring))
                        sstring = ""
            break
 
        if found == 0:
            irc.reply("Pokemon not found")
            return 0
        else:
            coefc = float(level)/100.00
            for i in bases:
                intercs.append(float(i)*float(level)/50.00)
        
            for i in range(0,6):
                ivrange = []
                if i == 0:
                    for j in range(1,32):
                        if (math.floor(coefc*j+intercs[i]+int(level)+10) == stats[i]):
                            ivrange.append(j)
                    low.append(ivrange[0])
                    high.append(ivrange[len(ivrange)-1])
                else:
                    for j in range(1,32):
                        if math.floor(natures[i]*(math.floor(coefc*j+intercs[i]+5))) == stats[i]:
                            ivrange.append(j)
                    low.append(ivrange[0])
                    high.append(ivrange[len(ivrange)-1])
 
        irc.reply(str(species + " (" + nature + "): HP: " + str(low[0]) + "-" + str(high[0]) + ", Atk: " + str(low[1]) + "-" + str(high[1]) + ", Def: " + str(low[2]) + "-" + str(high[2]) + ", S.Atk: " + str(low[3]) + "-" + str(high[3]) + ", S.Def: " + str(low[4]) + "-" + str(high[4]) + ", Spd: " + str(low[5]) + "-" + str(high[5])))
    
    iv = wrap(iv, ['something', 'something', 'something', 'something', 'something', 'something', 'something', 'something', 'something'])
    
    def basestats(self, irc, msg, args, poke):
        """<pokemon>
        
        Shows the base stats of the given pokemon
        """
        q = self._db(poke, "poke")[0]
        if q:
            msg = "HP: %s Atk: %s Def: %s Sp.Atk: %s SpDef: %s Spd: %s Total: %s Avg: %s" % (q[7], q[8], q[9], q[10], q[11], q[12], sum(q[7:13]), sum(q[7:13])/6)
            irc.reply(msg)
        else:
            irc.reply("Pokemon not found")
        
    basestats = wrap(basestats, ['something'])
    
    def type(self, irc, msg, args, poke):
        """<pokemon>
        
        Gives the Types of the pokemon.
        """
        query = self._db(poke)
        if query:
            irc.reply(query[5] + " " + query[6])
        else:
            irc.reply("Pokemon not found.")
    
    type = wrap(type, ['something'])
    
    def evolve(self, irc, msg, args, poke):
        """ <pokemon>
        
        Gives how to evolve a <pokemon>. If the pokemon can evolve 
        multiple times, every evolve is written on a seperate line.
        Pokemon evolve in 3 possible ways: Leveling, trading or stones.
        If an evolve doesn't say trade or stone, it always need to level
        up before it initiates the evolve. The text after "Trade" is
        always an item.
        """
        q = self._db(poke, "evos")
        if q:
            msg = poke + ' evolves into: '
            for a in q:
                irc.reply(msg + a[1] + ' -> ' + a[2])
        else:
            irc.reply('Error: Name wrong')
    
    evolve = wrap(evolve, ['something'])
    
    def loc(self, irc, msg, args, poke, game):
        """ <pokemon> [<game>]
        
        Gives the location of <pokemon>.
        If <game> is not set, it will be XY.
        Game should be noted as gencodes like RB, Y, DP, P, HGSS etc.
        Version 2.0 games like Yellow/Crystal are seperate.
        Y is version YELLOW. For version Y, use XY.
        """
        L = -1
        try:
            game = str.upper(game)
        except:
            game = 'XY'
        
        if game == 'XY' or game == 'X' or game == 'Y':
            L = -1
        if game == 'RED' or game == 'BLUE' or game == 'RB':
            L = 0
        if game == 'YELLOW' or game == 'Y':
            L = 2
        if game == 'GOLD' or game == 'SILVER' or game == 'GS':
            L = 3
        if game == 'CRYSTAL' or game == 'C':
            L = 4
        if game == 'RUBY' or game == 'SAPPHIRE' or game == 'RS':
            L = 5
        if game == 'EMERALD' or game == 'E':
            L = 6
        if game == 'FIRE RED' or game == 'LEAF GREEN' or game == 'FRLG':
            L = 7
        if game == 'DIAMOND' or game == 'PEARL' or game == 'DP':
            L = 10
        if game == 'PLATINUM' or game == 'P':
            L = 11
        if game == 'HG' or game == 'SS' or game == 'HGSS':
            L = 12
        if game == 'BLACK' or game == 'WHITE' or game == 'BW':
            L = 15
        if game == 'BLACK2' or game == 'WHITE2' or game == 'BW2' or game == 'B2W2':
            L = 16
        
        try:
            soup = BS(urlopen('http://bulbapedia.bulbagarden.net/wiki/'+ poke + '_(Pok%C3%A9mon)').read(), 'html.parser', parse_only=SS(class_='roundyright'))
            locs = soup.get_text().split('\n')
            locs = locs[:19]
            irc.reply(poke + ':' + re.sub(r'([a-z0-9])([A-Z])', '\\1 - \\2', locs[L]))
        except:
            irc.reply('This Pok\xE9mon does not exist')
        
    loc = wrap(loc, ['something', optional('something')])
    
    def defense(self, irc, msg, args, typ):
        """ <type>

        Function to get the weakness of a given type.
        Two types are possible to be set like "Fire Ground".
        """
        nrm = [1,1,1,1,1,1,2,1,1,1,1,1,1,0,1,1,1,1]
        fir = [1,0.5,2,1,0.5,0.5,1,1,2,1,1,0.5,2,1,1,1,0.5,0.5]
        wtr = [1,0.5,0.5,2,2,0.5,1,1,1,1,1,1,1,1,1,1,0.5,1]
        ele = [1,1,1,0.5,1,1,1,1,2,0.5,1,1,1,1,1,1,0.5,1]
        grs = [1,2,0.5,0.5,0.5,2,1,2,0.5,2,1,2,1,1,1,1,1,1]
        ice = [1,2,1,1,1,0.5,2,1,1,1,1,1,2,1,1,1,2,1]
        fig = [1,1,1,1,1,1,1,1,1,2,2,0.5,0.5,1,1,0.5,1,2]
        psn = [1,1,1,1,0.5,1,0.5,0.5,2,1,2,0.5,1,1,1,1,1,0.5]
        grd = [1,1,2,0,2,2,1,0.5,1,1,1,1,0.5,1,1,1,1,1]
        fly = [1,1,1,2,0.5,2,0.5,1,0,1,1,0.5,2,1,1,1,1,1]
        psy = [1,1,1,1,1,1,0.5,1,1,1,0.5,2,1,2,1,2,1,1]
        bug = [1,2,1,1,0.5,1,0.5,1,0.5,2,1,1,2,1,1,1,1,1]
        rck = [0.5,0.5,2,1,2,1,2,0.5,2,0.5,1,1,1,1,1,1,2,1]
        gho = [0,1,1,1,1,1,0,0.5,1,1,1,0.5,1,2,1,2,1,1]
        drg = [1,0.5,0.5,0.5,0.5,2,1,1,1,1,1,1,1,1,2,1,1,2]
        drk = [1,1,1,1,1,1,2,1,1,1,0,2,1,0.5,1,0.5,1,2]
        stl = [0.5,2,1,1,0.5,0.5,2,0,2,0.5,0.5,0.5,0.5,1,0.5,1,0.5,0.5]
        fai = [1,1,1,1,1,1,0.5,2,1,1,1,0.5,1,1,0,0.5,2,1]
        
        typ = typ.split()
        typ[0] = str.capitalize(typ[0])
        typeefc = [nrm, fir, wtr, ele, grs, ice, fig, psn, grd, fly, psy, bug, rck, gho, drg, drk, stl, fai]
        typnam = ['Normal', 'Fire', 'Water', 'Electric', 'Grass', 'Ice', 'Fighting', 'Poison', 'Ground', 'Flying', 'Psychic', 'Bug', 'Rock', 'Ghost', 'Dragon', 'Dark', 'Steel', 'Fairy']
        typshort = ['Nrm', 'Fir', 'Wtr', 'Ele', 'Gra', 'Ice', 'Fig', 'Psn', 'Gro', 'Fly', 'Psy', 'Bug', 'Rck', 'Gho', 'Dra', 'Drk', 'Stl', 'Fai']
        message = ""
        weak = []
        check = 0.0
        amount = 0
        try:
            typ[1] = str.capitalize(typ[1])
            weaklist = [a*b for a,b in zip(typeefc[typnam.index(typ[0])],typeefc[typnam.index(typ[1])])]
        except:
            weaklist = typeefc[typnam.index(typ[0])]
        
        while (check < 9):
            weak.append([])
            i = -1
            if check == 5:
                check = 8
            if check == 3:
                check = 4
            try:
                while 1:
                    i = weaklist.index(check / 2.0, i+1)
                    weak[amount].append(i)
            except ValueError:
                pass
            if check == 0 or check == 0.5:
                check += 0.5
            else:
                check += 1
            amount += 1
        
        if weak[0]:
            message += "0 damage: "
            for j in weak[0]:
                message += typnam[j] + " "
            message += "- "
        
        if weak[1]:
            message += "x\xBC damage: "
            for j in weak[1]:
                message += typnam[j] + " "
            message += "- "
        
        if weak[2]:
            message += "x\xBD damage: "
            for j in weak[2]:
                message += typnam[j] + " "
            message += "- "
        
        if weak[4]:
            message += "x2 Damage: "
            for j in weak[4]:
                message += typnam[j] + " "
        
        if weak[5]:
            message += "- "
            message += "x4 Damage: "
            for j in weak[5]:
                message += typnam[j] + " "
        
        irc.reply(message)
    defense = wrap(defense, ['text'])
    
    def attack(self, irc, msg, args, typ):
        """Function to get the weakness of a given type.
        """
        nrm = [1,1,1,1,1,1,1,1,1,1,1,1,0.5,0,1,1,0.5,1]
        fir = [1,0.5,0.5,1,2,2,1,1,1,1,1,2,0.5,1,0.5,1,2,1]
        wtr = [1,2,0.5,1,0.5,1,1,1,2,1,1,1,2,1,0.5,1,1,1]
        ele = [1,1,2,0.5,0.5,1,1,1,0,2,1,1,1,1,0.5,1,1,1]
        grs = [1,0.5,2,1,0.5,1,1,0.5,2,0.5,1,0.5,2,1,0.5,1,0.5,1]
        ice = [1,0.5,0.5,1,2,0.5,1,1,2,2,1,1,1,1,2,1,0.5,1]
        fig = [2,1,1,1,1,2,1,0.5,1,0.5,0.5,0.5,2,0,1,1,2,0.5]
        psn = [1,1,1,1,2,1,1,0.5,0.5,1,1,1,0.5,0.5,1,1,0,2]
        grd = [1,2,1,2,0.5,1,1,2,1,0,1,1,2,1,1,1,2,1]
        fly = [1,1,1,0.5,2,1,2,1,1,1,1,2,0.5,1,1,1,0.5,1]
        psy = [1,1,1,1,1,1,2,2,1,1,0.5,1,1,1,1,0,0.5,1]
        bug = [1,0.5,1,1,2,1,0.5,0.5,1,0.5,2,1,1,0.5,1,2,0.5,0.5]
        rck = [1,2,1,1,1,2,0.5,1,0.5,2,1,2,1,1,1,1,0.5,1]
        gho = [0,1,1,1,1,1,1,1,1,1,2,1,1,2,1,0.5,0.5,2]
        drg = [1,1,1,1,1,1,1,1,1,1,1,1,1,1,2,1,0.5,0]
        drk = [1,1,1,1,1,1,0.5,1,1,1,2,1,1,2,1,0.5,0.5,0.5]
        stl = [1,0.5,0.5,0.5,1,2,1,1,1,1,1,1,2,1,1,1,0.5,2]
        fai = [1,0.5,1,1,1,1,2,0.5,1,1,1,1,1,1,2,2,0.5,1]

        typeefc = [nrm, fir, wtr, ele, grs, ice, fig, psn, grd, fly, psy, bug, rck, gho, drg, drk, stl, fai]
        typnam = ['Normal', 'Fire', 'Water', 'Electric', 'Grass', 'Ice', 'Fighting', 'Poison', 'Ground', 'Flying', 'Psychic', 'Bug', 'Rock', 'Ghost', 'Dragon', 'Dark', 'Steel', 'Fairy']
        typshort = ['Nrm', 'Fir', 'Wtr', 'Ele', 'Gra', 'Ice', 'Fig', 'Psn', 'Gro', 'Fly', 'Psy', 'Bug', 'Rck', 'Gho', 'Dra', 'Drk', 'Stl', 'Fai']
        weak = []
        check = 0.0
        amount = 0
        
        while (check < 5):
            weak.append([])
            i = -1
            if check == 3:
                check += 1
            try:
                while 1:
                    i = typeefc[typnam.index(typ)].index(check / 2, i+1)
                    weak[amount].append(i)
            except ValueError:
                pass
            check += 1
            amount += 1
        
        message = ""
        
        if weak[0]:
            message += "No damage: "
            for j in weak[0]:
                message += typnam[j] + " "
            message += "- "
        
        if weak[1]:
            message += "Half damage: "
            for j in weak[1]:
                message += typnam[j] + " "
            message += "- "
        
        if weak[3]:
            message += "Double Damage: "
            for j in weak[3]:
                message += typnam[j] + " "

        irc.reply(message)
    attack = wrap(attack, ['something'])

Class = Pokemon

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
                cur.execute("SELECT * FROM formes WHERE PokeID=(SELECT ID FROM pokemon WHERE Name='%s')" % poke)
            if querytype == "TEST":
                cur.execute("" % poke)
            return cur.fetchall()
        except mdb.Error, e:
            return 0
        finally:
            if con:
                con.close()
    
    def _dbforme(self, poke, formetype):
        try:
            con = mdb.connect(dbip, dbuser, dbpass, dbname)
            cur = con.cursor()
            cur.execute("SELECT * FROM formes WHERE PokeID=(SELECT ID FROM pokemon WHERE Name='%s') AND Form='%s'" % (poke, formetype))
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
                msg2 = "Stats - HP: %s Atk: %s Def: %s Sp.Atk: %s Sp.Def: %s Spd: %s " % (i[5], i[6], i[7], i[8], i[9], i[10])
                irc.reply(msg)
                irc.reply(msg2)
        else:
            irc.reply("Pokemon has no Megavolve.")
            
    mega = wrap(mega, ['something'])
    
    def forme(self, irc, msg, args, poke):
        """<pokemon>
        
        Replies all the formes for given pokemon."""
        data = self._db(poke, "forme")
        if data:
            for i in data:
                msg = i[2] + ' ' + poke + ' '
                msg += '- Type: ' + i[3] 
                if i[4]:
                    msg += '/' + i[4]
                msg2 = "Stats - HP: %s Atk: %s Def: %s Sp.Atk: %s Sp.Def: %s Spd: %s " % (i[5], i[6], i[7], i[8], i[9], i[10])
                irc.reply(msg)
                irc.reply(msg2)
        else:
            irc.reply("Pokemon has no formes.")
    
    forme = wrap(forme, ['something'])
    
    def _ivcalc(self, poke, stat, amount, level, nature, ev):
        poke = poke.split(' ')
        formes = ['SANDY', 'TRASH', 'SUNNY', 'RAINY', 'SNOWY', 'ATTACK', \
                  'DEFENSE', 'SPEED', 'HEAT', 'WASH', 'FROST', 'FAN', 'MOW', \
                  'ORIGIN', 'SKY', 'ZEN', 'THERIAN', 'BLACK', 'WHITE', \
                  'PIROUETTE', 'BLADE', 'AVERAGE', 'LARGE', 'SUPER']
        sts = ('HP', 'ATK', 'DEF', 'STK', 'SDF', 'SPD')
        natures = ('LONELY', 'BRAVE', 'ADAMANT', 'NAUGHTY', 'BOLD', 'RELAXED', 'IMPISH', 'LAX', 'MODEST', 'MILD', 'QUIET', 'RASH', 'CALM', 'GENTLE', 'SASSY', 'CAREFUL', 'TIMID', 'HASTY', 'JOLLY', 'NAIVE')
        natureP = ('ATK','ATK','ATK','ATK','DEF','DEF','DEF','DEF','SPD','SPD','SPD','SPD','STK','STK','STK','STK','SPF','SPF','SPF','SPF')
        natureM = ('DEF','SPD','STK','SDF','ATK','SPD','STK','SDF','ATK','DEF','STK','SDF','ATK','DEF','SPD','SDF','ATK','DEF','SPD','STK')
        extra = 5
        hp = 0
        
        if not ev: ev = 0
        
        # Mega was added for compatability reasons, because it's only avaiable in battle, it's not very useful.
        if poke[0].upper() == 'MEGA':
            if len(poke) > 2:
                stats = self._db(poke[1], poke[2].upper())[0][5:11]
            else:
                stats = self._db(poke[1], 'mega')[0][5:11]
        elif poke[0].upper() in formes:
            stats = self._dbforme(poke[1], poke[0])[5:11]
        else:
            stats = self._db(poke[0], 'poke')[0][7:13]
        
        b = natures.index(nature.upper())
        if natureP[b] == stat.upper():
            bonus = 1.1
        elif natureM[b] == stat.upper():
            bonus = 0.9
        else:
            bonus = 1
        if stat == 'HP':
            extra = 10
            hp = 100
        
        return (((amount - ((2 * stats[sts.index(stat.upper())] + (ev / 4) + hp) * level * bonus / 100) - extra * bonus) * 100) / bonus) / level
        
    def reverseiv(self, irc, msg, args, poke, stat, iv, level, nature, ev):
        """<[forme] pokemon> <stat> <iv> <level> <nature> <[ev]>
        
        Calculates the stat given the IV/EV/Nature/Level. If EV is empty, 
        it will be 0. Quick fix, nature-bonus should be set manually (0.9, 1 or 1.1)
        """
        
        if not ev: ev = 0
        poke = poke.split(' ')
        formes = ['SANDY', 'TRASH', 'SUNNY', 'RAINY', 'SNOWY', 'ATTACK', \
                  'DEFENSE', 'SPEED', 'HEAT', 'WASH', 'FROST', 'FAN', 'MOW', \
                  'ORIGIN', 'SKY', 'ZEN', 'THERIAN', 'BLACK', 'WHITE', \
                  'PIROUETTE', 'BLADE', 'AVERAGE', 'LARGE', 'SUPER']
        natures = ('LONELY', 'BRAVE', 'ADAMANT', 'NAUGHTY', 'BOLD', 'RELAXED', 'IMPISH', 'LAX', 'MODEST', 'MILD', 'QUIET', 'RASH', 'CALM', 'GENTLE', 'SASSY', 'CAREFUL', 'TIMID', 'HASTY', 'JOLLY', 'NAIVE')
        natureP = ('ATK','ATK','ATK','ATK','DEF','DEF','DEF','DEF','SPD','SPD','SPD','SPD','STK','STK','STK','STK','SPF','SPF','SPF','SPF')
        natureM = ('DEF','SPD','STK','SDF','ATK','SPD','STK','SDF','ATK','DEF','STK','SDF','ATK','DEF','SPD','SDF','ATK','DEF','SPD','STK')
        sts = ('HP', 'ATK', 'DEF', 'STK', 'SDF', 'SPD')
        
        if poke[0].upper() == 'MEGA':
            if len(poke) > 2:
                stats = self._db(poke[1], poke[2].upper())[0][5:11]
            else:
                stats = self._db(poke[1], 'mega')[0][5:11]
        elif poke[0].upper() in formes:
            stats = self._dbforme(poke[1], poke[0])[5:11]
        else:
            stats = self._db(poke[0], 'poke')[0][7:13]
        
        b = natures.index(nature.upper())
        if natureP[b] == stat.upper():
            bonus = 1.1
        elif natureM[b] == stat.upper():
            bonus = 0.9
        else:
            bonus = 1
        
        amount = (((iv + (2 * stats[sts.index(stat.upper())]) + ev/4) * level * bonus) / 100 + 5) * bonus
        
        irc.reply(str(amount))
        
    reverseiv = wrap(reverseiv, ['something', 'something', 'int', 'int', 'something', optional('int')])
        
    def ivsingle(self, irc, msg, args, poke, stat, amount, level, nature, ev):
        """<[forme] pokemon> <stat> <amount> <level> <nature> <[ev]>
        
        Calculates the IV of a stat with given pokemon/level/nature.
        Stat is "HP/ATK/DEF/STK/SDF/SPD". If EV is empty, it will be 0.
        If pokemon has a forme (like Mega), capture it like "Mega Charizard X"
        or "Trash Wormadam" (plant is default).
        """
        if not ev: ev = 0
        IV = self._ivcalc(poke, stat, amount, level, nature, ev)
        irc.reply(stat + ': ' + str(IV))
        
    ivsingle = wrap(ivsingle, ['something', 'something', 'int', 'int', 'something', optional('int')])
    
    def iv(self, irc, msg, args, poke, level, nature, hp, atk, defe, spa, spd, spe, ev):
        """ <pokemon> <level> <nature> <hp> <atk> <def> <sp.atk> <sp.def> <spd>
        
        Calculates possible IVs of a given pokemon. Please insert all stats. 
        EV optional, else it will be 0.
        """
        if not ev: ev = 0
        
        HP = self._ivcalc(poke, 'HP', hp, level, nature, ev)
        ATK = self._ivcalc(poke, 'ATK', atk, level, nature, ev)
        DEF = self._ivcalc(poke, 'DEF', defe, level, nature, ev)
        STK = self._ivcalc(poke, 'STK', spa, level, nature, ev)
        SDF = self._ivcalc(poke, 'SDF', spd, level, nature, ev)
        SPD = self._ivcalc(poke, 'SPD', spe, level, nature, ev)
        
        irc.reply('HP: ' + str(HP) + ' ATK: ' + str(ATK) + ' DEF: ' + str(DEF) + ' STK: ' + str(STK) + ' SDF: ' + str(SDF) + ' SPD: ' + str(SPD))
        
    iv = wrap(iv, ['something', 'int', 'something', 'int', 'int', 'int', 'int', 'int', 'int', optional('int')])
    
    def basestats(self, irc, msg, args, poke):
        """<pokemon>
        
        Shows the base stats of the given pokemon. If the pokemon has a 
        forme or mega, capture it with " (e.g. !basestats "Sandy Wormadam"
        or "!basestats "Mega Mewtwo X"
        """
        poke = poke.split(' ')
        formes = ['SANDY', 'TRASH', 'SUNNY', 'RAINY', 'SNOWY', 'ATTACK', \
            'DEFENSE', 'SPEED', 'HEAT', 'WASH', 'FROST', 'FAN', 'MOW', \
            'ORIGIN', 'SKY', 'ZEN', 'THERIAN', 'BLACK', 'WHITE', \
            'PIROUETTE', 'BLADE', 'AVERAGE', 'LARGE', 'SUPER']
        if poke[0].upper() == 'MEGA':
            if len(poke) > 2:
                q = self._db(poke[1], poke[2].upper())[0]
            else:
                q = self._db(poke[1], 'mega')[0]
        elif poke[0].upper() in formes:
            q = self._dbforme(poke[1], poke[0])[0]
        else:
            q = self._db(poke[0], 'poke')[0]
        q = q[-6:]
        msg = "HP: %s Atk: %s Def: %s Sp.Atk: %s SpDef: %s Spd: %s Total: %s Avg: %s" % (q[0], q[1], q[2], q[3], q[4], q[5], sum(q[0:5]), sum(q[0:5])/6)
        irc.reply(msg)
        
    basestats = wrap(basestats, ['something'])
    
    def type(self, irc, msg, args, poke):
        """<pokemon>
        
        Gives the Types of the pokemon.
        Please use "forme or mega" to check the type of a forme/mega.
        """
        try:
            query = self._db(poke, 'poke')[0]
            irc.reply(query[5] + " " + query[6])
        except IndexError:
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
            irc.reply('No evolution found.')
    
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
        
        if typ[0] not in typnam:
            a = self._db(typ[0], 'poke')[0]
            if a:
                typ[0] = a[5]
                typ.append(a[6])
        
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
        """<type>
        
        Function to get the weakness of a given type.
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
    
    def smogon(self, irc, msg, args, poke, gen):
        """<pokemon> [<gen>]
        
        Retrieves the Tier of the given pokemon for the given gen.
        If no gen is given, will default to gen 5 (BW)
        """
        g = ['bw','rb','gs','rs','dp','bw','xy']
        try:
            gen = g[int(gen)]
        except:
            gen = 'bw'
        url = "http://www.smogon.com/%s/pokemon/%s" % (gen, poke)
        try:
            soup = BS(urlopen(url).read(), 'html.parser', parse_only=SS(class_="info"))
            irc.reply('Gen: ' + gen.upper() + ' Tier: '+ soup.get_text().split('\n\n')[3] + " url: " + url)
        except:
            irc.reply('Something went wrong.')
    smogon = wrap(smogon, ['something', optional('something')])
    
    def ev(self, irc, msg, args, poke):
        """<pokemon>
        
        Outputs the amount of EV this pokemon will give when defeated.
        """
        # Probably some way to do this better
        msg = ""
        i = 0
        Type = [' HP ', ' Atk ', ' Def ', ' SpAtk ', ' SpDef ', ' Spd ']
        EV = self._db(poke, "poke")[0][13].split(',')

        while i < 6:
            if int(EV[i]) > 0:
                msg += Type[i] + EV[i]
            i += 1

        irc.reply(poke + " yields:" + msg)
    ev = wrap(ev, ['something'])
        
    
Class = Pokemon

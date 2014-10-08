import string

class MRFW:
    """
    A toolbox of useful functions for the FW.
    Should probably be more structured, or not
    set as a bunch of static methods...
    """

    @staticmethod
    def is_type(thing, type):
        try:
            if thing.__class__.fancy_name == type:
                return True
        except:
            pass
        return False

    @staticmethod
    def is_room(thing):
        return MRFW.is_type(thing, "room")

    @staticmethod
    def is_thing(thing):
        return MRFW.is_type(thing, "thing")

    @staticmethod
    def is_player(thing):
        return MRFW.is_type(thing, "player")

    @staticmethod
    def match_name(short, name):
        if short == name[:len(short)]:
            return True
        return False

    @staticmethod
    def get_first_arg(data):
        words = data.split()
        if len(words) < 1:
            raise EmptyArgException()
        return words[0]

    @staticmethod
    def multiple_choice(choices):
        names = map(lambda x:x.name, choices)
        return "Which one?\nChoices are: " + string.join(names, ', ')


# A bunch of exceptions... quite handy
class AmbiguousException(Exception):
    def __init__(self, choices):
        self.choices = choices

class NotFoundException(Exception):
    pass

class EmptyArgException(Exception):
    pass


class MRObject(object):
    """
    The base object class of the world.
    Every object belonging to the world
    should inherit from this class
    """

    fancy_name = "object"
    cmds = {}

    def __init__(self, name):
        self.name = name


class MRThing(MRObject):
    """
    Things that are not players or rooms.
    Usually common objects, usable or not.
    """

    fancy_name = "thing"

    def __init__(self, name):
        super(MRThing, self).__init__(name)
        self.description = "A boring non-descript thing."


class MRRoom(MRObject):
    """
    The parent class for every room of
    the world. Any room should inherit
    from this class.
    """

    fancy_name = "room"
    cmds = {"say":"cmd_say"}

    def __init__(self, name):
        super(MRRoom, self).__init__(name)
        self.contents = []
        self.description = "A blank room."

    def cmd_say(self, player, rest):
        self.broadcast(player.name + " says: " + rest)

    def broadcast(self, msg):
        for thing in filter(MRFW.is_player, self.contents):
            thing.send(msg)


class MRPlayer(MRObject):
    fancy_name = "player"
    cmds = {"look":"cmd_look", 
            "go":"cmd_go", 
            'describe':'cmd_describe',
            "destroy":"cmd_destroy"}

    def __init__(self, name):
        super(MRPlayer, self).__init__(name)
        self.description = "A non-descript citizen."
        self.client = None
        self.room = None

    def __getstate__(self):
        odict = self.__dict__.copy()
        del odict['client']
        return odict

    def __setstate__(self, dict):
        self.__dict__.update(dict)
        self.client = None

    def send(self, msg):
        if self.client != None:
            self.client.send(msg)

    def find_thing(self, name):
        if name == "me" or name == self.name:
            return self
        if self.room == None:
            raise NotFoundException()
        if name == "here":
            return self.room
        match = filter(lambda x:MRFW.match_name(name, x.name), self.room.contents)
        if len(match) > 1:
            raise AmbiguousException(match)
        if len(match) < 1:
            raise NotFoundException()
        return match[0]

    def cmd_describe(self, player, rest):
        try:
            what = MRFW.get_first_arg(rest)
            thing = self.find_thing(what)
        except AmbiguousException, ex:
            self.send(MRFW.multiple_choice(ex.choices))
        except NotFoundException:
            self.send("You see nothing like '" + what + "' here.")
        except EmptyArgException:
            self.send("Describe what?")
        else:
            thing.description = string.join(rest.split()[1:])

    def cmd_go(self, player, rest):
        try:
            what = MRFW.get_first_arg(rest)
        except EmptyArgException:
            self.send("Go where?")
            return
        found = MRDB.search(what, MRRoom)
        if len(found) < 1:
            self.send("Don't know this place. Is it in Canada?")
        elif len(found) > 1:
            self.send(MRFW.multiple_choice(found))
        else:
            if self.room != None:
                self.room.contents.remove(self)
                self.room.broadcast(self.name + ' has gone to ' + found[0].name) 
                found[0].broadcast(self.name + ' arrives from ' + self.room.name) 
            else:
                found[0].broadcast(self.name + ' pops into the room')
            self.room = found[0]
            self.room.contents.append(self)

    def cmd_destroy(self, player, rest):
        try:
            what = MRFW.get_first_arg(rest)
            thing = self.find_thing(what)
        except AmbiguousException, ex:
            self.send(MRFW.multiple_choice(ex.choices))
        except NotFoundException:
            self.send("You see nothing like '" + what + "' here.")
        except EmptyArgException:
            self.send("Destroy what?")
        else:
            if self.room != None:
                self.room.broadcast(self.name + " violently destroyed " + thing.name + "!")
                if MRFW.is_room(thing):
                    self.room.broadcast("You are expulsed into the void of nothingness.")
                    for p in filter(MRFW.is_player, thing.contents):
                        p.room = None
                else:
                    self.room.contents.remove(thing)
            MRDB.objects.remove(thing)
            if MRFW.is_player(thing):
                if thing.client != None:
                    thing.client.player = None
                    thing.send("Your player has been slain. You were kicked out of it")


    def cmd_look(self, player, rest):
        try:
            what = MRFW.get_first_arg(rest)
        except EmptyArgException:
            what = "here"
        if what == "here":
            if self.room == None:
                self.send("You only see nothing. A lot of nothing.")
            else:
                self.send(self.room.name + ": " + self.room.description)
                if len(self.room.contents) == 0:
                    self.send("It is empty")
                else:
                    self.send("Contents:")
                for thing in self.room.contents:
                    self.send(" - " + thing.name)
        elif what == "me" or what==self.name:
                self.send(self.name + ": " + self.description)
        else:
            if self.room == None:
                self.send("You see nothing but you.")
            else:
                try:
                    thing = self.find_thing(what)
                except AmbiguousException, ex:
                    self.send(MRFW.multiple_choice(ex))
                except NotFoundException:
                    self.send("You see nothing like '" + what + "' here.")
                else:
                    self.send(thing.name + ": " + thing.description)


class MRDB:
    """
    The class holding the world.
    This class shares an interface with the
    server and should inherit from such
    an interface...
    """

    classes = [MRThing, MRRoom, MRPlayer]
    objects = []

    @staticmethod
    def search(name, type = MRObject):
        found = []
        for thing in MRDB.objects:
            if MRFW.match_name(name, thing.name):
                if isinstance(thing, type):
                    found.append(thing)
        return found

    @staticmethod
    def list_all(type):
        return MRDB.search("", type)


class MRClient:
    """
    This class is one of the only interfaces
    between the FW and the server.
    Ideally, it should derive from a basic
    class implementing but the minimum needed
    stuff needed for the server to work...
    """

    cmds = {'chat':'cmd_chat', 
            'name':'cmd_name',
            'help':'cmd_help',
            'create':'cmd_create',
            'play':'cmd_play',
            'eval':'cmd_eval',
            'exec':'cmd_exec'}

    player = None
    op = False

    def __init__(self, handler, name):
        self.handler = handler
        self.name = name
        handler.server.cr.broadcast(name + " connected!")
        self.id = handler.server.cr.get_uid()

    def cmd_chat(self, rest):
        self.handler.server.cr.broadcast("[global] " + self.name + 
                " says: " + rest)

    def cmd_name(self, rest):
        words = rest.split()
        if len(words) < 1:
            self.send("Again?")
        else:
            self.name = words[0]

    def cmd_help(self, rest):
        self.send("chat <text>           global chat\n"
                  "name <name>           change your client name\n"
                  "exec <command>        execute python command\n"
                  "create <type> <name>  thing, player, or room\n"
                  "play <name>           go in the shoes of a player\n"
                  "go <place>            move to a room\n"
                  "look                  in a room, look around")

    def cmd_create(self, rest):
        words = rest.split()
        if len(words) < 2:
            self.send("Cannot create a nameless thing...")
            return
        cls = filter(lambda x:MRFW.match_name(words[0], x.fancy_name), MRDB.classes)
        if len(cls) != 1:
            self.send("Create a what?")
        else:
            if len(MRDB.search(words[1])) > 0:
                self.send("Uhm... something by that name already exists...")
                return
            thing = cls[0](words[1])
            MRDB.objects.append(thing)
            if MRFW.is_thing(thing) and self.player != None:
                if self.player.room != None:
                    self.player.room.contents.append(thing)

    def cmd_play(self, rest):
        try:
            who = MRFW.get_first_arg(rest)
        except EmptyArgException:
            self.send("Play who?")
            return
        found = MRDB.search(who, MRPlayer)
        if len(found) < 1:
            self.send("Couldn't find the guy.")
        elif len(found) > 1:
            self.send(MRFW.multiple_choice(found))
        else:
            if self.player != None:
                self.player.client = None
            self.player = found[0]
            found[0].client = self

    def cmd_eval(self, rest):
        try:
            self.send(str(eval(rest)))
        except Exception, pbm:
            self.send(str(pbm))

    def cmd_exec(self, rest):
        try:
            exec(rest.replace('\\n','\n').replace('\\t','\t'))
        except Exception, pbm:
            self.send(str(pbm))

    def handle_input(self, data):
        cmds = {}
        for k in self.cmds.keys():
            cmds[k] = self
        if self.player != None:
            for k in self.player.cmds.keys():
                cmds[k] = self.player
            if self.player.room != None:
                for k in self.player.room.cmds.keys():
                    cmds[k] = self.player.room
        words = data.split()
        match = filter(lambda x:MRFW.match_name(words[0], x), cmds.keys())
        if len(match) != 1:
            self.send("Huh?")
            return
        if cmds[match[0]] == self:
            cmd = getattr(self, self.cmds[match[0]])
            cmd(string.join(words[1:]))
        else:
            t = cmds[match[0]]
            cmd = getattr(t, t.cmds[match[0]])
            cmd(self.player, string.join(words[1:]))

    def is_op(self):
        return self.op

    def send(self, msg):
        try:
            self.handler.wfile.write(msg + "\n")
        except:
            print "Could not send to " + self.name

    def on_disconnect(self):
        if self.player != None:
            self.player.client = None

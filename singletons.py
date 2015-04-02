__author__ = 'latty'


class SingletonDecorator:
    """
    # url: http://python-3-patterns-idioms-test.readthedocs.org/en/latest/Singleton.html

    """

    def __init__(self, klass):
        """

        :param klass:

        """
        self.klass = klass
        self.instance = None

    def __call__(self, *args, **kwds):
        """

        :param args:
        :param kwds:

        """
        if self.instance is None:
            self.instance = self.klass(*args, **kwds)
        return self.instance


class Borg:
    """
    # Google Developers Day US - Python Design Patterns
    # video : https://www.youtube.com/watch?v=0vJJlVBVTFg#t=14m38s

    """
    __shared_state = {}
    # init internal state variables here
    __register = {}
    def __init__(self):
        """

        """
        self.__dict__ = self.__shared_state
        if not self.__register:
            self._init_default_register()


#Unique Pattern
class Unique:
    #Define some static variables here
    x = 1
    @classmethod
    def init(cls):
        #Define any computation performed when assigning to a "new" object
        return cls


class Singleton(object):
    """
    url: http://code.activestate.com/recipes/52558-the-singleton-pattern-implemented-with-python/

    """
    __single = None     # the one, true Singleton
    #
    def __new__(classtype, *args, **kwargs):
        # Check to see if a __single exists already for this class
        # Compare class types instead of just looking for None so
        # that subclasses will create their own __single objects
        if classtype != type(classtype.__single):
            classtype.__single = object.__new__(classtype, *args, **kwargs)
        return classtype.__single
    #
    def __init__(self, name=None):
        self.name = name
    #
    def display(self):
        print self.name, id(self), type(self)


import thread


class MySingletonClass_with_Inheritance_support(object):
    '''Implement Pattern: SINGLETON'''
    __lockObj = thread.allocate_lock()  # lock object
    __instance = None  # the unique instance
    #
    # def __new__(cls, *args, **kargs):
    def __new__(cls):
        # return cls.getInstance(cls, *args, **kargs)
        return cls.getInstance(cls)
    #
    def __init__(self):
        pass
    #
    @staticmethod
    def _initialize_():
        print "_initialize_ from 'MySingletonClass_with_Inheritance_support'"
    #
    @classmethod
    # def getInstance(cls, *args, **kargs):
    def getInstance(cls):
        '''Static method to have a reference to **THE UNIQUE** instance'''
        # Critical section start
        cls.__lockObj.acquire()
        try:
            # Check to see if a __instance exists already for this class
            # Compare class types instead of just looking for None so
            # that subclasses will create their own __instance objects
            #if cls.__instance is None:
            if cls != type(cls.__instance):
                # (Some exception may be thrown...)
                # Initialize **the unique** instance
                # cls.__instance = object.__new__(cls, *args, **kargs)
                cls.__instance = object.__new__(cls)
                '''Initialize object **here**, as you would do in __init__()...'''
                cls._initialize_()
        finally:
            #  Exit from critical section whatever happens
            cls.__lockObj.release()
            pass
        # Critical section end
        return cls.__instance


class Singleton: pass
Singleton = MySingletonClass_with_Inheritance_support


class SubSingleton(Singleton):
    @staticmethod
    def _initialize_():
        print "_initialize_ from 'SubSingleton'"
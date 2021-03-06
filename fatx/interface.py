import os
from .blocks import DirectoryEntry, DirectoryEntryList

"""
This file contains four classes which are used as the main interface for 
the user of FATX-on-a-snake. 
Actually, I lied, you are only supposed to interact with three
of them, since FatxObject is the common baseclass from wich the others
extend. My reasoning behind this is, that in FATX you only interact with
"DirectoryEntrys" which are always the same, no matter if they are a file
or a directory. So it makes sense to me that they should share a similar
interface which subclasses extend to implement specific behavior. 
The functions of the classes are described in the README, how ever since 
you are already here, take a look at FatxObject and read the comments on 
the methodes. :)

"""


class FatxObject():
	_filesystem = None

	@classmethod
	def registerFilesystem(cls, fs):
		cls._filesystem = fs

	@staticmethod
	def splitPath(path):
		segments = path.split('/')
		while '' in segments:
			segments.remove('')
		return segments

	# Note: static typing with selfreference(for parent) is possible but ugly :(
	def __init__(self, directoryentry: DirectoryEntry, parent): 
		self._de = directoryentry
		self._name = self._de.filename
		self.attributes = self._de.atr
		self._parent = parent

	def ls(self, deleted=False):
		"""
		if self is a directory, this should list all items
		in this directory
		"""
		raise NotImplementedError("Override this in the subclass")

	def details(self):
		"""
		Prints its own attributes
		"""
		return self._de.atr.__dict__

	def parent(self):
		"""
		parent() should return the FatxObject that can point to
		this object(parent dir)
		"""
		return self._parent

	def get(self, path):
		"""
		returns the FatxObject for a given path(or file)
		"""
		raise NotImplementedError("Override this in the subclass")

	def rename(self, name):
		"""
		renames this object and safes the change to disk
		"""
		self._filesystem.rename(self._de, name)

	def exportFile(self):
		"""
		returns all bytes belonging to this file
		"""
		raise NotImplementedError("Override this in the subclass")

	def importFile(self, data, filename):
		"""
		imports a given data-bytearray to filename into this folder
		"""
		raise NotImplementedError("Override this in the subclass")

	def delete(self):
		"""
		Marks this object as deleted and safes change to disk
		"""
		raise NotImplementedError("Override this in the subclass")

	def __str__(self):
		return self._de.filename

	def __repr__(self):
		return str(self.__class__)+ ': ' + str(self)


class FileObject(FatxObject):

	def ls(self, deleted=False):
		import pdb
		pdb.Pdb().set_trace()
		raise TypeError("This is a file, not a directory")

	def get(self, path):
		# since every FatxObject has the scope "/" as root(itself), asking for "/" should yield yourself
		segments = self.splitPath(path)
		if len(segments) == 0:
			return self
		raise TypeError("This is a file, not a directory(Note: use .exportFile() to extract my contents!")

	def exportFile(self):
		return self._filesystem.readFile(self._de)


class DirectoryObject(FatxObject):
	"""
	 This class represents directorys of the filesystem. 
	"""
	def __init__(self, directoryentry: DirectoryEntry, parent: FatxObject): # directorylist: DirectoryEntryList):
		super().__init__(directoryentry, parent)

		# get a list of all files in the subdir, note: You'll get a DirectoryEntryList(DEL) in return
		# This DEL enables you to append files and writing them to disk
		self._dl = self._filesystem.openDirectory(directoryentry)
		
		# Prepare a list of FatxObjects for easy access later on
		self._elements = []
		self.createFatxObjectList()

	def createFatxObjectList(self):
		for i in self._dl.list():
			if i.atr.DIRECTORY:
				self._elements.append(DirectoryObject(i, self))
			else:
				self._elements.append(FileObject(i, self))

	def ls(self, path="/", deleted=False):
		obj = self.get(path)
		if isinstance(obj, DirectoryObject):
			return [ i for i in obj._elements if (not i.attributes.DELETED or deleted)]
		else:
			raise ValueError("Not a directory")

	def get(self, path):
		def filterByName(name):
			for i in self._elements:
				if i._name == name:
					return i
			raise IndexError()
		segments = self.splitPath(path)
		if len(segments) > 0:
			subnames = [i._name for i in self._elements]
			if segments[0] in subnames:
				try:
					return filterByName(segments[0]).get(path.replace(segments[0], '', 1))
				except ValueError as e:
					raise e
			else:
				raise ValueError("Path not found")
		else:
			return self

	def importFile(self, path):
		filename = os.path.basename(path)
		if filename in [i._name for i in self._elements]:
			raise SystemError("File already exists")
		file = open(path, 'rb')
		# create new directory entry for the new file
		size = os.stat(filename).st_size
		newDE = DirectoryEntry.new(size, filename)
		# write file data to disk
		clusterStartID = self._filesystem.writeFile(file, size)
		newDE.cluster = clusterStartID
		self._dl.append(newDE)
		self._filesystem.writeDirectoryEntryList(self._dl)
		
		# update our entrys
		self._elements = []
		self.createFatxObjectList()


class RootObject(DirectoryObject):
	"""
	 This class should only be instantiated once, as it is the root of the entire filesystem
	 Only the init behaves diffrent compared to a regular DirectoryObject, as the root does
	 not have its own DirectoryEntry
	"""
	def __init__(self, directorylist: DirectoryEntryList):
		self._parent = self
		self._dl = directorylist
		self._elements = []
		self.createFatxObjectList()

	def details(self):
		raise TypeError("This is your root!")

	def rename(self, name):
		raise TypeError("You can't rename the filesystem root")

	def __str__(self):
		return "Root of the filesystem"


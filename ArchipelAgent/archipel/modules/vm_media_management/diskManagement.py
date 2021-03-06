#!/usr/bin/python
# archipelModuleHypervisorTest.py
# 
# Copyright (C) 2010 Antoine Mercadal <antoine.mercadal@inframonde.eu>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
# 
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


# we need to import the package containing the class to surclass
from archipel.utils import *
import xmpp
import archipel.core
import commands
import os, sys


ARCHIPEL_ERROR_CODE_DRIVES_CREATE       = -3001
ARCHIPEL_ERROR_CODE_DRIVES_DELETE       = -3002
ARCHIPEL_ERROR_CODE_DRIVES_GET          = -3003
ARCHIPEL_ERROR_CODE_DRIVES_GETISO       = -3004
ARCHIPEL_ERROR_CODE_DRIVES_CONVERT      = -3005
ARCHIPEL_ERROR_CODE_DRIVES_RENAME       = -3006

class TNMediaManagement:
    
    def __init__(self, shared_isos_folder, entity):
        """
        initialize the module
        @type entity TNArchipelEntity
        @param entity the module entity
        """
        self.entity = entity
        self.shared_isos_folder =  shared_isos_folder
        
        # permissions 
        self.entity.permission_center.create_permission("drives_create", "Authorizes user to get create a drive", False)
        self.entity.permission_center.create_permission("drives_delete", "Authorizes user to delete a drive", False)
        self.entity.permission_center.create_permission("drives_get", "Authorizes user to get all drives", False)
        self.entity.permission_center.create_permission("drives_getiso", "Authorizes user to get existing ISO images", False)
        self.entity.permission_center.create_permission("drives_convert", "Authorizes user to convert a drive", False)
        self.entity.permission_center.create_permission("drives_rename", "Authorizes user to rename a drive", False)
    
    
    
    ### XMPP Processing
    
    
    def process_iq(self, conn, iq):
        """
        Invoked when new ARCHIPEL_NS_VM_DISK IQ is received.
        
        it understands IQ of type:
        - create
        - delete
        - get
        - getiso
        - convert
        - rename
        
        @type conn: xmpp.Dispatcher
        @param conn: ths instance of the current connection that send the message
        @type iq: xmpp.Protocol.Iq
        @param iq: the received IQ
        """
        action = self.entity.check_acp(conn, iq)
        self.entity.check_perm(conn, iq, action, -1, prefix="drives_")
        
        if self.entity.is_migrating and (not action in ("get", "getiso")): reply = build_error_iq(self, "virtual machine is migrating. Can't perform any drives operation", iq, ARCHIPEL_NS_ERROR_MIGRATING)
        elif action == "create":    reply = self.iq_create(iq)
        elif action == "delete":    reply = self.iq_delete(iq)
        elif action == "get":       reply = self.iq_get(iq)
        elif action == "getiso":    reply = self.iq_getiso(iq)
        elif action == "convert":   reply = self.iq_convert(iq)
        elif action == "rename":    reply = self.iq_rename(iq)
        
        if reply:
            conn.send(reply)
            raise xmpp.protocol.NodeProcessed
    
    
    def iq_create(self, iq):
        """
        Create a disk in given format
        
        @type iq: xmpp.Protocol.Iq
        @param iq: the received IQ
        
        @rtype: xmpp.Protocol.Iq
        @return: a ready to send IQ containing the result of the action
        """
        try:
            query_node  = iq.getTag("query")
            disk_name   = query_node.getTag("archipel").getAttr("name").replace(" ", "_").replace("/", "_").replace("..", "_")
            disk_size   = query_node.getTag("archipel").getAttr("size")
            disk_unit   = query_node.getTag("archipel").getAttr("unit")
            format      = query_node.getTag("archipel").getAttr("format")
            disk_path   = self.entity.folder + "/" + disk_name + "." + format
            
            if disk_unit == "M" and (int(disk_size) >= 1000000000):
                raise Exception("too big",  "You may be able to do it manually, but I won't try")
            elif disk_unit == "G" and (int(disk_size) >= 10000):
                raise Exception("too big", "You may be able to do this manually, but I won't try")
            
            if os.path.exists(disk_path):
                raise Exception("The disk with name %s already exists." % disk_name)
            
            ret = os.system("qemu-img create -f " + format + " " + disk_path + " " + disk_size + disk_unit)
            
            if not ret == 0:
                raise Exception("DriveError", "Unable to create drive. Error code is " + str(ret))
         
            reply = iq.buildReply("result")
            self.entity.log.info("disk created")
            self.entity.shout("disk", "I've just created a new hard drive named %s with size of %s%s." % (disk_name, disk_size, disk_unit), excludedgroups=['vitualmachines'])
            self.entity.push_change("disk", "created", excludedgroups=['vitualmachines'])
        except Exception as ex:
            reply = build_error_iq(self, ex, iq, ARCHIPEL_ERROR_CODE_DRIVES_CREATE)
        return reply
    
    
    def iq_convert(self, iq):
        """
        Convert a disk from a format to another
        
        @type iq: xmpp.Protocol.Iq
        @param iq: the received IQ
        
        @rtype: xmpp.Protocol.Iq
        @return: a ready to send IQ containing the result of the action
        """
        try:
            old_status  = self.entity.xmppstatus
            old_show    = self.entity.xmppstatusshow
            query_node  = iq.getTag("query")
            path        = query_node.getTag("archipel").getAttr("path")
            format      = query_node.getTag("archipel").getAttr("format")
            disk_path   = path.replace(path.split(".")[-1], "") + format
            
            if os.path.exists(disk_path):
                raise Exception("The disk with same name and extension already exists.")
                
            self.entity.change_presence(presence_show="dnd", presence_status="Converting a disk...")
            ret = os.system("qemu-img convert " + path + " -O " + format + " " + disk_path)
            if not ret == 0:
                raise Exception("DriveError", "Unable to convert drive. Error code is " + str(ret))
            
            os.unlink(path)
                        
            self.entity.change_presence(presence_show=old_show, presence_status=old_status)
            reply = iq.buildReply("result")
            self.entity.log.info("convertion of  created")
            self.entity.shout("disk", "I've just converted hard drive %s into format %s." % (path, format), excludedgroups=['vitualmachines'])
            self.entity.push_change("disk", "converted", excludedgroups=['vitualmachines'])
        except Exception as ex:
            self.entity.change_presence(presence_show=old_show, presence_status=old_status)
            reply = build_error_iq(self, ex, iq, ARCHIPEL_ERROR_CODE_DRIVES_CONVERT)
        return reply
    
    
    def iq_rename(self, iq):
        """
        Rename a disk
        
        @type iq: xmpp.Protocol.Iq
        @param iq: the received IQ
        
        @rtype: xmpp.Protocol.Iq
        @return: a ready to send IQ containing the result of the action
        """
        try:
            query_node = iq.getTag("query")
            path = query_node.getTag("archipel").getAttr("path")
            newname = query_node.getTag("archipel").getAttr("newname")
            
            extension = path.split(".")[-1]
            newpath = os.path.join(self.entity.folder,  "%s.%s" % (newname, extension))
            
            if os.path.exists(newpath):
                raise Exception("The disk with name %s already exists." % newname)
            
            os.rename(path, newpath)
            
            reply = iq.buildReply("result")
            self.entity.log.info("renamed hard drive %s into  %s" % (path, newname))
            self.entity.shout("disk", "I've just renamed hard drive %s into  %s." % (path, newname), excludedgroups=['vitualmachines'])
            self.entity.push_change("disk", "renamed", excludedgroups=['vitualmachines'])
        except Exception as ex:
            reply = build_error_iq(self, ex, iq, ARCHIPEL_ERROR_CODE_DRIVES_RENAME)
        return reply
    
    
    def iq_delete(self, iq):
        """
        delete a virtual hard drive
        
        @type iq: xmpp.Protocol.Iq
        @param iq: the received IQ
        
        @rtype: xmpp.Protocol.Iq
        @return: a ready to send IQ containing the result of the action
        """
        try:
            query_node          = iq.getTag("query")
            disk_name           = query_node.getTag("archipel").getAttr("name")
            secure_disk_name    = disk_name.split("/")[-1]
            secure_disk_path    = self.entity.folder + "/" + secure_disk_name
            
            old_status  = self.entity.xmppstatus
            old_show    = self.entity.xmppstatusshow
            self.entity.change_presence(presence_show="dnd", presence_status="Deleting a drive...")
            
            os.system("rm -rf " + secure_disk_path)
            
            disk_nodes = []
            if self.entity.definition:
                devices_node = self.entity.definition.getTag('devices')
                disk_nodes = devices_node.getTags('disk', attrs={'type': 'file'})
            
            if query_node.getTag("archipel").getAttr("undefine") ==  "yes":
                have_undefined_at_least_on_disk = False
                for disk_node in disk_nodes:
                    path = disk_node.getTag('source').getAttr('file')
                    if path == secure_disk_path:
                        devices_node.delChild(disk_node)
                        have_undefined_at_least_on_disk = True
                
                if have_undefined_at_least_on_disk:
                    xml = str(self.entity.definition).replace('xmlns="http://www.gajim.org/xmlns/undeclared" ', '')
                    self.entity.libvirt_connection.defineXML(xml)
                    self.entity.push_change("virtualmachine:definition", "defined", excludedgroups=['vitualmachines'])
            
            self.entity.change_presence(presence_show=old_show, presence_status=old_status)
            
            reply = iq.buildReply("result")
            self.entity.log.info("disk %s deleted" % secure_disk_path)
            self.entity.push_change("disk", "deleted", excludedgroups=['vitualmachines'])
            self.entity.shout("disk", "I've just deleted the hard drive named %s." % (disk_name), excludedgroups=['vitualmachines'])
        except Exception as ex:
            reply = build_error_iq(self, ex, iq, ARCHIPEL_ERROR_CODE_DRIVES_DELETE)
        return reply
    
    
    def iq_get(self, iq):
        """
        Get the virtual hatd drives of the virtual machine
        
        @type iq: xmpp.Protocol.Iq
        @param iq: the received IQ
        
        @rtype: xmpp.Protocol.Iq
        @return: a ready to send IQ containing the result of the action
        """
        try:
            disks = commands.getoutput("ls " + self.entity.folder).split()
            nodes = []
        
            for disk in disks:
                file_cmd_output = commands.getoutput("file " + self.entity.folder + "/" + disk).lower()
                
                if (file_cmd_output.find("format: qcow") > -1 \
                or file_cmd_output.find("boot sector") > -1 \
                or file_cmd_output.find("vmware") > -1\
                or file_cmd_output.find("data") > -1\
                or file_cmd_output.find("user-mode linux cow file") > -1) \
                and file_cmd_output.find("sqlite") == -1:
                    diskinfo = commands.getoutput("qemu-img info " + self.entity.folder + "/" + disk).split("\n")
                    node = xmpp.Node(tag="disk", attrs={ "name": disk.split('.')[0],
                        "path": self.entity.folder + "/" + disk,
                        "format": diskinfo[1].split(": ")[1],
                        "virtualSize": diskinfo[2].split(": ")[1],
                        "diskSize": diskinfo[3].split(": ")[1],
                    })
                    nodes.append(node)
        
            reply = iq.buildReply("result")
            reply.setQueryPayload(nodes)
            self.entity.log.info("info about disks sent")
        except Exception as ex:
            reply = build_error_iq(self, ex, iq, ARCHIPEL_ERROR_CODE_DRIVES_GET)
        return reply
    
    
    def iq_getiso(self, iq):
        """
        Get the virtual cdrom ISO of the virtual machine
        
        @type iq: xmpp.Protocol.Iq
        @param iq: the received IQ
        
        @rtype: xmpp.Protocol.Iq
        @return: a ready to send IQ containing the result of the action
        """
        try:
            nodes = []
        
            isos = commands.getoutput("ls " + self.entity.folder).split()
            for iso in isos:
                if commands.getoutput("file " + self.entity.folder + "/" + iso).lower().find("iso 9660") > -1:
                    node = xmpp.Node(tag="iso", attrs={"name": iso, "path": self.entity.folder + "/" + iso })
                    nodes.append(node)
        
            sharedisos = commands.getoutput("ls " + self.shared_isos_folder).split() 
            for iso in sharedisos:
                if commands.getoutput("file " + self.shared_isos_folder + "/" + iso).lower().find("iso 9660") > -1:
                    node = xmpp.Node(tag="iso", attrs={"name": iso, "path": self.shared_isos_folder + "/" + iso })
                    nodes.append(node)
        
            reply = iq.buildReply("result")
            reply.setQueryPayload(nodes)
            self.entity.log.info("info about iso sent")
        except Exception as ex:
            reply = build_error_iq(self, ex, iq, ARCHIPEL_ERROR_CODE_DRIVES_GETISO)
        return reply
    




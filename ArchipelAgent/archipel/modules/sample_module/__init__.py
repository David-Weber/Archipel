#!/usr/bin/python
# 
# __init__.py
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


import archipel.core.archipelHypervisor

import sampleModule


ARCHIPEL_NS_SAMPLE = "a:type:that:doesnt:exists"

# this method will be call at loading
def __module_init__sample_module(self):
    self.log.info("hello from sample module")
    self.module_sample = sampleModule.TNSampleModule(self)

# this method will be called at registration of handlers for XMPP
def __module_register_stanza__sample_module(self):
    self.xmppclient.RegisterHandler('iq', self.module_sample.process_iq, ns=ARCHIPEL_NS_SAMPLE)



# WARNING THIS WILL CHANGE SOON.
# finally, we add the methods to the class
setattr(archipel.core.archipelHypervisor.TNArchipelHypervisor, "__module_init__sample_module", __module_init__sample_module)
setattr(archipel.core.archipelHypervisor.TNArchipelHypervisor, "__module_register_stanza__sample_module", __module_register_stanza__sample_module)
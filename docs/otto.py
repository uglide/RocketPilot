# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Autopilot Functional Test Tool
# Copyright (C) 2012-2013 Canonical
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


from docutils import nodes
from sphinx.util.compat import Directive
from sphinx.util.compat import make_admonition


def setup(app):
    app.add_node(otto,
                 html=(visit_todo_node, depart_todo_node),
                 latex=(visit_todo_node, depart_todo_node),
                 text=(visit_todo_node, depart_todo_node))

    app.add_directive('otto', OttoSaysDirective)

    app.add_stylesheet('otto.css')


class otto(nodes.Admonition, nodes.Element):
    pass


def visit_todo_node(self, node):
    self.visit_admonition(node)


def depart_todo_node(self, node):
    self.depart_admonition(node)


class OttoSaysDirective(Directive):

    # this enables content in the directive
    has_content = True

    def run(self):
        ad = make_admonition(otto, self.name, ['Autopilot Says'], self.options,
                             self.content, self.lineno, self.content_offset,
                             self.block_text, self.state, self.state_machine)
        image_container = nodes.container()
        image_container.append(nodes.image(uri='/images/otto-64.png'))
        image_container['classes'] = ['otto-image-container']
        outer_container = nodes.container()
        outer_container.extend([image_container] + ad)
        outer_container['classes'] = ['otto-says-container']
        return [outer_container]

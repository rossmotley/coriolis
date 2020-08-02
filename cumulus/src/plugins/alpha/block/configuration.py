#
# This file is part of the Coriolis Software.
# Copyright (c) SU 2020-2020, All Rights Reserved
#
# +-----------------------------------------------------------------+
# |                   C O R I O L I S                               |
# |      C u m u l u s  -  P y t h o n   T o o l s                  |
# |                                                                 |
# |  Author      :                    Jean-Paul CHAPUT              |
# |  E-mail      :            Jean-Paul.Chaput@lip6.fr              |
# | =============================================================== |
# |  Python      :       "./plugins/block/configuration.py"         |
# +-----------------------------------------------------------------+


import sys
import os.path
import Cfg
from   Hurricane import Breakpoint
from   Hurricane import DbU
from   Hurricane import Box
from   Hurricane import Transformation
from   Hurricane import Box
from   Hurricane import Path
from   Hurricane import Layer
from   Hurricane import Occurrence
from   Hurricane import Net
from   Hurricane import NetExternalComponents
from   Hurricane import RoutingPad
from   Hurricane import Horizontal
from   Hurricane import Vertical
from   Hurricane import Contact
from   Hurricane import Pin
from   Hurricane import Plug
from   Hurricane import Instance
import CRL
from   CRL                 import RoutingLayerGauge
from   helpers             import trace, l, u, n
from   helpers.io          import ErrorMessage
from   helpers.io          import WarningMessage
from   helpers.io          import catch
from   helpers.overlay     import CfgCache
from   plugins             import getParameter
from   plugins.alpha.utils import getPlugByName


# ----------------------------------------------------------------------------
# Class  :  "configuration.GaugeConf".

class GaugeConf ( object ):
    """
    Wrapper around the Cell and I/O pads RoutingGauge, with additional
    services.

    The Cell routing gauge is read from the configuration parameter
    ``anabatic.routingGauge``.
    """

    HAccess         = 0x0001
    OffsetRight1    = 0x0002
    OffsetTop1      = 0x0004
    OffsetBottom1   = 0x0008
    DeepDepth       = 0x0010
    UseContactWidth = 0x0020
    ExpandWidth     = 0x0040

    def __init__ ( self ):
        self._cellGauge      = None
        self._ioPadGauge     = None
        self._routingGauge   = None
        self._topLayerDepth  = 0
        self._plugToRp       = { }
        self._rpToAccess     = { }
        self._loadRoutingGauge()
        return

    @property
    def routingGauge  ( self ): return self._routingGauge

    @property
    def sliceHeight   ( self ): return self._cellGauge.getSliceHeight()

    @property
    def sliceStep     ( self ): return self._cellGauge.getSliceStep()

    @property
    def ioPadHeight   ( self ): return self._ioPadGauge.getSliceHeight()

    @property
    def ioPadStep     ( self ): return self._ioPadGauge.getSliceStep()

    @property
    def ioPadPitch    ( self ): return self._ioPadGauge.getPitch()

    @property
    def ioPadGauge    ( self ): return self._ioPadGauge

    @property
    def hRoutingGauge ( self ): return self._routingGauge.getLayerGauge( self.horizontalDepth )

    @property
    def vRoutingGauge ( self ): return self._routingGauge.getLayerGauge( self.verticalDepth )

    @property
    def hDeepRG       ( self ): return self._routingGauge.getLayerGauge( self.horizontalDeepDepth )

    @property
    def vDeepRG       ( self ): return self._routingGauge.getLayerGauge( self.verticalDeepDepth )

    def getPitch ( self, layer ): return self._routingGauge.getPitch( layer )

    def _loadRoutingGauge ( self ):
        trace( 550, ',+', '\tGaugeConf._loadRoutingGauge()\n' )
        gaugeName = Cfg.getParamString('anabatic.routingGauge').asString()
        self._cellGauge    = CRL.AllianceFramework.get().getCellGauge( gaugeName )
        self._routingGauge = CRL.AllianceFramework.get().getRoutingGauge( gaugeName )

        if not self._routingGauge:
            trace( 500, '-' )
            raise ErrorMessage( 1, [ 'RoutingGauge._loadRoutingGauge(): No routing gauge named "{}".'.format(gaugeName)
                                   , 'Please check the "anabatic.routingGauge" configuration parameter." ' ])

        topLayer = Cfg.getParamString('anabatic.topRoutingLayer').asString()

        self.topLayerDepth = 0
        for layerGauge in self._routingGauge.getLayerGauges():
            if layerGauge.getLayer().getName() == topLayer:
                self.topLayerDepth = layerGauge.getDepth()
                break
        if not self.topLayerDepth:
            print WarningMessage( 'Gauge top layer not defined, using top of gauge ({}).' \
                                  .format(self._routingGauge.getDepth()) )
            self._topLayerDepth = self._routingGauge.getDepth() - 1

        self.horizontalDepth     = -1
        self.verticalDepth       = -1
        self.horizontalDeepDepth = -1
        self.verticalDeepDepth   = -1
        for depth in range(0,self.topLayerDepth+1):
            trace( 550, '\tdepth:{} {}\n'.format(depth,self._routingGauge.getLayerGauge(depth) ))
            
            if self._routingGauge.getLayerGauge(depth).getType() == RoutingLayerGauge.PinOnly:
                continue
            if self._routingGauge.getLayerGauge(depth).getDirection() == RoutingLayerGauge.Horizontal:
                if self.horizontalDeepDepth < 0:
                    self.horizontalDeepDepth = depth
                self.horizontalDepth = depth
            if self._routingGauge.getLayerGauge(depth).getDirection() == RoutingLayerGauge.Vertical:
                if self.verticalDeepDepth < 0:
                    self.verticalDeepDepth = depth
                self.verticalDepth = depth
        trace( 550, '\t| horizontalDepth    :{}\n'.format(self.horizontalDepth) )
        trace( 550, '\t| verticalDepth      :{}\n'.format(self.verticalDepth) )
        trace( 550, '\t| horizontalDeepDepth:{}\n'.format(self.horizontalDeepDepth) )
        trace( 550, '\t| verticalDeepDepth  :{}\n'.format(self.verticalDeepDepth) )
        trace( 500, '-' )
        return

    def _loadIoPadGauge ( self, ioPadGaugeName ):
        self._ioPadGauge = CRL.AllianceFramework.get().getCellGauge( ioPadGaugeName )
        if not self._ioPadGauge:
            print WarningMessage( 'IO pad gauge "%s" not found.' % ioPadGaugeName )
        return

    def isHorizontal ( self, layer ):
        mask = layer.getMask()
        for lg in self._routingGauge.getLayerGauges():
            if lg.getLayer().getMask() == mask:
                if lg.getDirection() == RoutingLayerGauge.Horizontal: return True
                return False
        
        print ErrorMessage( 1, 'GaugeConf.isHorizontal(): Layer "%s" is not part of gauge "%s", cannot know preferred direction.' \
                                % (layer.getName(), self._routingGauge.getName()) )
        return False

    def isVertical ( self, layer ): return not self.isHorizontal( layer )

    def createContact ( self, net, x, y, flags ):
        if flags & GaugeConf.DeepDepth: depth = self.horizontalDeepDepth
        else:                           depth = self.horizontalDepth

        if self.horizontalDepth > self.verticalDepth: depth -= 1

        trace( 550, '\t%s, horizontalDepth:%d, gaugeDepth:%d\n'
               % (self._routingGauge,self.horizontalDepth,self._routingGauge.getDepth()))
        return Contact.create( net
                             , self._routingGauge.getContactLayer(depth)
                             , x, y
                             , self._routingGauge.getLayerGauge(depth).getViaWidth()
                             , self._routingGauge.getLayerGauge(depth).getViaWidth()
                             )

    def getNearestHorizontalTrack ( self, bb, y, flags ):
        if flags & GaugeConf.DeepDepth: depth = self.horizontalDeepDepth
        else:                           depth = self.horizontalDepth
        
        index = self._routingGauge.getLayerGauge(depth).getTrackIndex( bb.getYMin()
                                                                     , bb.getYMax()
                                                                     , y
                                                                     , RoutingLayerGauge.Nearest )
        return self._routingGauge.getLayerGauge(depth).getTrackPosition( bb.getYMin(), index )

    def getNearestVerticalTrack ( self, bb, x, flags ):
        if flags & GaugeConf.DeepDepth: depth = self.verticalDeepDepth
        else:                           depth = self.verticalDepth
        
        index = self._routingGauge.getLayerGauge(depth).getTrackIndex( bb.getXMin()
                                                                     , bb.getXMax()
                                                                     , x
                                                                     , RoutingLayerGauge.Nearest )
        return self._routingGauge.getLayerGauge(depth).getTrackPosition( bb.getXMin(), index )

    def createHorizontal ( self, source, target, y, flags ):
        if flags & GaugeConf.DeepDepth: depth = self.horizontalDeepDepth
        else:                           depth = self.horizontalDepth
        
        layer = self._routingGauge.getRoutingLayer(depth)
        
        if flags & GaugeConf.UseContactWidth:
            width = source.getBoundingBox(layer.getBasicLayer()).getHeight()
        else:
            width = self._routingGauge.getLayerGauge(depth).getWireWidth()
        if flags & GaugeConf.ExpandWidth:
            width += DbU.fromLambda( 1.0 )
        
        segment = Horizontal.create( source, target, layer, y, width )
        trace( 550, segment )
        return segment
  
    def createVertical ( self, source, target, x, flags ):
        if flags & GaugeConf.DeepDepth: depth = self.verticalDeepDepth
        else:                           depth = self.verticalDepth
        
        layer = self._routingGauge.getRoutingLayer(depth)
        
        if flags & GaugeConf.UseContactWidth:
            width = source.getBoundingBox(layer.getBasicLayer()).getWidth()
        else:
            width = self._routingGauge.getLayerGauge(depth).getWireWidth()
        if flags & GaugeConf.ExpandWidth:
            width += DbU.fromLambda( 1.0 )
        
        segment = Vertical.create( source, target, layer, x, width )
        trace( 550, segment )
        return segment
  
    def rpAccess ( self, rp, flags ):
        trace( 550, ',+', '\t_rpAccess() %s\n' % str(rp) )
  
        if self._rpToAccess.has_key(rp):
            trace( 550, '-' )
            return self._rpToAccess[rp]
  
        if flags & GaugeConf.DeepDepth:
            hdepth = self.horizontalDeepDepth
            vdepth = self.verticalDeepDepth
        else:
            hdepth = self.horizontalDepth
            vdepth = self.verticalDepth
  
        hpitch    = self._routingGauge.getLayerGauge(hdepth).getPitch()
        hoffset   = self._routingGauge.getLayerGauge(hdepth).getOffset()
        contact1  = Contact.create( rp, self._routingGauge.getContactLayer(0), 0, 0 )
        midSliceY = contact1.getY() - (contact1.getY() % self._cellGauge.getSliceHeight()) \
                                                       + self._cellGauge.getSliceHeight() / 2
        midTrackY = midSliceY - ((midSliceY - hoffset) % hpitch)
        dy        = midSliceY - contact1.getY()
    
        if flags & GaugeConf.OffsetBottom1: dy += hpitch
        if flags & GaugeConf.OffsetTop1:    dy -= hpitch
        contact1.setDy( dy )
  
        trace( 550, contact1 )
    
        if flags & GaugeConf.HAccess: stopDepth = hdepth
        else:                         stopDepth = vdepth
        trace( 550, '\tstopDepth:%d\n' % stopDepth )
  
        for depth in range(1,stopDepth):
            xoffset = 0
            if flags & GaugeConf.OffsetRight1 and depth == 1:
                xoffset = self._routingGauge.getLayerGauge(depth+1).getPitch()
            contact2 = Contact.create( rp.getNet()
                                     , self._routingGauge.getContactLayer(depth)
                                     , contact1.getX() + xoffset
                                     , contact1.getY()
                                     , self._routingGauge.getLayerGauge(depth).getViaWidth()
                                     , self._routingGauge.getLayerGauge(depth).getViaWidth()
                                     )
            trace( 550, contact2 )
            if self._routingGauge.getLayerGauge(depth).getDirection() == RoutingLayerGauge.Horizontal:
                segment = Horizontal.create( contact1
                                           , contact2
                                           , self._routingGauge.getRoutingLayer(depth)
                                           , contact1.getY()
                                           , self._routingGauge.getLayerGauge(depth).getWireWidth()
                                           )
                trace( 550, segment )
            else:
                segment = Vertical.create( contact1
                                         , contact2
                                         , self._routingGauge.getRoutingLayer(depth)
                                         , contact1.getX()
                                         , self._routingGauge.getLayerGauge(depth).getWireWidth()
                                         )
                trace( 550, segment )
            contact1 = contact2
  
        self._rpToAccess[rp] = contact1
    
        trace( 550, '-' )
        return contact1
  
    def rpByOccurrence ( self, occurrence, net ):
        plug = occurrence.getEntity()
        if self._plugToRp.has_key(plug):
            rp = self._plugToRp[plug]
        else:
            rp = RoutingPad.create( net, occurrence, RoutingPad.BiggestArea )
            self._plugToRp[plug] = rp
        return rp
  
    def rpAccessByOccurrence ( self, occurrence, net, flags ):
        plug = occurrence.getEntity()
        if self._plugToRp.has_key(plug):
            rp = self._plugToRp[plug]
        else:
            rp = RoutingPad.create( net, occurrence, RoutingPad.BiggestArea )
            self._plugToRp[plug] = rp
        return self.rpAccess( self._rpByOccurrence(occurrence,net), flags )
  
    def rpByPlug ( self, plug, net ):
        if self._plugToRp.has_key(plug):
            rp = self._plugToRp[plug]
        else:
            occurrence = Occurrence( plug, Path(net.getCell(),'') )
            rp         = RoutingPad.create( net, occurrence, RoutingPad.BiggestArea )
            self._plugToRp[plug] = rp
        return rp
  
    def rpByPlugName ( self, instance, plugName, net ):
        return self.rpByPlug( getPlugByName(instance,plugName), net )
  
    def rpAccessByPlug ( self, plug, net, flags ):
        return self.rpAccess( self.rpByPlug(plug,net), flags )
  
    def rpAccessByPlugName ( self, instance, plugName, net, flags=0 ):
        return self.rpAccess( self.rpByPlugName(instance,plugName,net), flags )

    def setStackPosition ( self, topContact, x, y ):
        topContact.setX( x )
        topContact.setY( y )
        
        count = 0
        for component in topContact.getSlaveComponents():
            segment = component
            count  += 1
        if count > 1:
          raise ErrorMessage( 1, 'GaugeConf::_setStackPosition(): There must be exactly one segment connected to %s, not %d.' % (topContact,count) )
        
        if count == 1:
            if isinstance(segment,Horizontal):
                segment.setY( y )
                segment.getOppositeAnchor( topContact ).setY( y )
            elif isinstance(segment,Vertical):
                segment.setX( x )
                segment.getOppositeAnchor( topContact ).setX( x )
        return


# ----------------------------------------------------------------------------
# Class  :  "configuration.BufferInterface".

class BufferInterface ( object ):

    def __init__ ( self, framework ):
        trace( 550, ',+', '\tBufferInterface.__init__()\n' )
        self.masterCell = framework.getCell( Cfg.getParamString('clockTree.buffer').asString()
                                     , CRL.Catalog.State.Views )
        if not self.masterCell:
            trace( 550, '-' )
            raise ErrorMessage( 3, [ 'ClockTree: Buffer cell "{}" not found in library,' \
                                     .format(Cfg.getParamString('clockTree.buffer').asString())
                                   , '           please check the "clockTree.buffer" configuration parameter in "plugins.conf".' ] )
        trace( 550, '\tmasterCell :<{}>\n'.format(self.masterCell) ) 
        
        self.count  = 0
        self.input  = None
        self.output = None
        for net in self.masterCell.getNets():
            if not net.isExternal(): continue
            if     net.isGlobal(): continue
            if     net.getDirection() & Net.Direction.IN:  self.input  = net.getName()
            elif   net.getDirection() & Net.Direction.OUT: self.output = net.getName()
        
        trace( 550, '\tinput :<{}>\n'.format(self.input ) ) 
        trace( 550, '\toutput:<{}>\n'.format(self.output) ) 
        trace( 550, '-' )
        return

    @property
    def width ( self ): return self.masterCell.getAbutmentBox().getWidth()

    @property
    def height ( self ): return self.masterCell.getAbutmentBox().getHeight()

    def createBuffer ( self, cell ):
        instance = Instance.create( cell, 'spare_buffer_{}'.format(self.count), self.masterCell )
        self.count += 1
        return instance


# ----------------------------------------------------------------------------
# Class  :  "configuration.IoPin".

class IoPin ( object ):
    """
    Create an I/O Pin on a side of a block for one net or a vector of nets.
    """

    SOUTH   = 0x0001
    NORTH   = 0x0002
    EAST    = 0x0004
    WEST    = 0x0008
    A_BEGIN = 0x0010
    A_END   = 0x0020
    A_MASK  = A_BEGIN|A_END

    def __init__ ( self, flags, stem, upos, ustep=0, count=1 ):
        """
        Create an I/O Pin(s) on the abutment box of a block. Could be for one
        net or a vector of net.

        :param flags: On which side the pin is to be put (SOUTH, NORTH, EAST or WEST).
        :param stem:  A string giving the name of the net. In case of a vector, it
                      must be a string containing exactly one '{}' as placeholder
                      for the index. 
        :param upos:  Offset from the bottom or left corner of the abutment box side.
        :param ustep: Distance between two consecutive Pins of the vector.
        :param count: Either an integer to be passed to ```range()``` or directly
                      a list of indexes.

        Examples:

        .. code-block:: python

           IoPin( IoPin.WEST , 'debug({})', l(50.0), l(100.0), 16 )
           IoPin( IoPin.EAST , 'debug(0)' , l(45.0),       0 ,  1 )
           IoPin( IoPin.SOUTH, 'adrs({})' , l(50.0), l(100.0), [0, 2, 3, 6] )
        """
        if   flags & IoPin.SOUTH: pass
        elif flags & IoPin.NORTH: pass
        elif flags & IoPin.EAST:  pass
        elif flags & IoPin.WEST:  pass
        else:
            raise ErrorMessage( 1, [ 'IoPin.__init__(): Unsupported direction {} for "{}"'.format(flags,stem)
                                   , '(must be NORTH, SOUTH, EAST or WEST)' ] )
        self.flags = flags
        self.pins  = []
        self.stem  = stem
        self.upos  = upos
        self.ustep = ustep
        self.count = count
        if self.upos == 0 and not (self.flags & IoPin.A_MASK):
            raise ErrorMessage( 1, [ 'IoPin.__init__(): "upos" parameter cannot be zero, corners are forbidden.'
                                   , 'For net "{}"'.format(stem) ] )
        if self.count > 1 and (self.ustep == 0) and not (self.flags & IoPin.A_MASK):
            raise ErrorMessage( 1, [ 'IoPin.__init__(): "ustep" parameter cannot be zero when "count" more than 1.'
                                   , 'For net "{}"'.format(stem) ] )

    @property
    def indexes ( self ):
        if isinstance(self.count,int):
            return range(self.count)
        return self.count

#   def place ( self, block ):
#       """
#       Performs the actual creation of the Pin. Should be called prior to any
#       call to ```Etesian.place()```, so the Pin is taken into account when building
#       the RoutingPads. Returns the number of *failed* pins, so zero means that all
#       went well... Currently only check for out of bounds coordinates.
#       """
#
#       if   self.flags & IoPin.SOUTH: side = block.sides[IoPin.SOUTH]
#       elif self.flags & IoPin.NORTH: side = block.sides[IoPin.NORTH]
#       elif self.flags & IoPin.EAST:  side = block.sides[IoPin.EAST ]
#       elif self.flags & IoPin.WEST:  side = block.sides[IoPin.WEST ]
#       status = 0
#       if isinstance(self.count,int):
#           indexes = range(self.count)
#       else:
#           indexes = self.count
#       if self.flags & (IoPin.NORTH | IoPin.SOUTH):
#           gauge = block.state.gaugeConf.vDeepRG
#           for index in indexes:
#               pinName  = self.stem.format(index)
#               net      = block.state.cell.getNet( pinName )
#               if net is None:
#                   print( ErrorMessage( 1, [ 'IoPin.place(): No net named "{}".'.format(pinName) ] ))
#                   continue
#               pinName += '.{}'.format(block.state.getIoPinsCounts(net))
#               pinPos   = side.getNextPinPosition( self.flags, self.upos, self.ustep )
#               if pinPos.getX() > block.state.xMax or pinPos.getX() < block.state.xMin:
#                   print( ErrorMessage( 1, [ 'IoPin.place(): Pin "{}" is outside north or south abutment box side.'.format(pinName)
#                                           , '(x:"{}", AB xMax:{})'.format(DbU.getValueString(pinPos.getX()),DbU.getValueString(block.state.xMax)) ] ))
#                   status += 1
#               trace( 550, '\tIoPin.place() N/S @{} "{}" of "{}".\n'.format(pinPos,pinName,net) )
#               pin = Pin.create( net
#                               , pinName
#                               , side.pinDirection
#                               , Pin.PlacementStatus.FIXED
#                               , gauge.getLayer()
#                               , pinPos.getX()
#                               , pinPos.getY()
#                               , gauge.getWireWidth()
#                               , gauge.getWireWidth() / 2
#                               )
#               NetExternalComponents.setExternal( pin )
#               side.append( self.flags, pin )
#               block.state.incIoPinsCounts( net )
#               if self.upos: self.upos + self.ustep
#       else:
#           gauge = block.state.gaugeConf.hDeepRG
#           for index in indexes:
#               pinName  = self.stem.format(index)
#               net      = block.state.cell.getNet( pinName )
#               if net is None:
#                   print( ErrorMessage( 1, [ 'IoPin.place(): No net named "{}".'.format(pinName) ] ))
#                   continue
#               pinName += '.{}'.format(block.state.getIoPinsCounts(net))
#               pinPos   = side.getNextPinPosition( self.flags, self.upos, self.ustep )
#               if pinPos.getY() > block.state.yMax or pinPos.getY() < block.state.yMin:
#                   print( ErrorMessage( 1, [ 'IoPin.place(): Pin "{}" is outside east or west abutment box side.'.format(pinName)
#                                           , '(y:"{}", AB yMax:{})'.format(DbU.getValueString(pinPos.getY()),DbU.getValueString(block.state.yMax)) ] ))
#                   status += 1
#               trace( 550, '\tIoPin.place() E/W @{} "{}" of "{}".\n'.format(pinPos,pinName,net) )
#               pin = Pin.create( net
#                               , pinName
#                               , side.pinDirection
#                               , Pin.PlacementStatus.FIXED
#                               , gauge.getLayer()
#                               , pinPos.getX()
#                               , pinPos.getY()
#                               , gauge.getWireWidth() / 2
#                               , gauge.getWireWidth()
#                               )
#               NetExternalComponents.setExternal( pin )
#               side.append( self.flags, pin )
#               block.state.incIoPinsCounts( net )
#               if self.upos: self.upos + self.ustep
#       return status


# ----------------------------------------------------------------------------
# Class  :  "configuration.BlockState".

class BlockState ( object ):
    """
    BlockState centralize all the configurations informations related to a
    given block.

    It contains:

    =================  ========================================
    Attribute          Information
    =================  ========================================
    ``framework``      The Framework we are using.
    ``gaugeConf``      The routing Gauge & Cell gauge.
    ``bufferConf``     The interface of the buffer cell.
    ``cell``           The block we are working on.
    =================  ========================================
    """
    
    def __init__ ( self, cell, ioPins=[] ):
        self.editor       = None
        self.framework    = CRL.AllianceFramework.get()
        self.cfg          = CfgCache('')
        self.gaugeConf    = GaugeConf()
        self.bufferConf   = BufferInterface( self.framework )
        self.cell         = cell
        self.fixedWidth   = None
        self.fixedHeight  = None
        self.deltaAb      = [ 0, 0, 0, 0 ]
        self.useClockTree = False
        self.useSpares    = True
        self.isBuilt      = False
        self.ioPins       = []
        self.ioPinsCounts = {}
        for ioPinSpec in ioPins:
            self.ioPins.append( IoPin( *ioPinSpec ) )

        self.cfg.etesian.aspectRatio = None
        self.cfg.etesian.spaceMargin = None
        self.cfg.block.spareSide     = None

    @property
    def bufferWidth ( self ): return self.bufferConf.width

    @property
    def bufferHeight ( self ): return self.bufferConf.height

    @property
    def xMin ( self ): return self.cell.getAbutmentBox().getXMin()

    @property
    def yMin ( self ): return self.cell.getAbutmentBox().getYMin()

    @property
    def xMax ( self ): return self.cell.getAbutmentBox().getXMax()

    @property
    def yMax ( self ): return self.cell.getAbutmentBox().getYMax()

    def setEditor ( self, editor ): self.editor = editor

    def createBuffer ( self ):
        return self.bufferConf.createBuffer( self.cell )

    def setDeltaAb ( self, dx1, dy1, dx2, dy2 ):
        self.deltaAb = [ dx1, dy1, dx2, dy2 ]

    def incIoPinsCounts ( self, net ):
        if not self.ioPinsCounts.has_key(net):
            self.ioPinsCounts[net] = 0
        self.ioPinsCounts[net] += 1

    def getIoPinsCounts ( self, net ):
        if not self.ioPinsCounts.has_key(net): return 0
        return self.ioPinsCounts[net]
import os
import unittest
import math
from __main__ import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging

#
# RobotPlacementSimulator
#

class RobotPlacementSimulator(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "Robot Placement Simulator" # TODO make this more human readable by adding spaces
    self.parent.categories = ["IGT"]
    self.parent.dependencies = []
    self.parent.contributors = ["Laurent Chauvin (BWH)"] # replace with "Firstname Lastname (Organization)"
    self.parent.helpText = """
    This is an example of scripted loadable module bundled in an extension.
    It performs a simple thresholding on the input volume and optionally captures a screenshot.
    """
    self.parent.acknowledgementText = """
    This file was originally developed by Laurent Chauvin (BWH) and was partially funded by NIH grant 3P41RR013218-12S1.
""" # replace with organization, grant and thanks.

#
# RobotPlacementSimulatorWidget
#

class RobotPlacementSimulatorWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)

    # Instantiate and connect widgets ...

    #
    # Parameters Area
    #
    parametersCollapsibleButton = ctk.ctkCollapsibleButton()
    parametersCollapsibleButton.text = "Parameters"
    self.layout.addWidget(parametersCollapsibleButton)

    # Layout within the dummy collapsible button
    parametersFormLayout = qt.QFormLayout(parametersCollapsibleButton)

    #
    # Place Sphere Button
    #
    self.placeSphereButton = qt.QPushButton()
    self.placeSphereButton.setText("Place Entry Point");
    self.placeSphereButton.setToolTip( "Place the entry point the robot is gonna be centered at." )
    parametersFormLayout.addRow(self.placeSphereButton)

    #
    # Sphere Radius Widget
    #
    self.sphereRadiusWidget = ctk.ctkSliderWidget()
    self.sphereRadiusWidget.singleStep = 1.0
    self.sphereRadiusWidget.minimum = 1
    self.sphereRadiusWidget.maximum = 100
    self.sphereRadiusWidget.value = 40
    self.sphereRadiusWidget.setToolTip("Set radius of the spherical ROI")
    parametersFormLayout.addRow("Sphere Radius", self.sphereRadiusWidget)

    #
    # Input Model
    #
    self.inputModel = slicer.qMRMLNodeComboBox()
    self.inputModel.nodeTypes = ( ("vtkMRMLModelNode"), "" )
    self.inputModel.selectNodeUponCreation = True
    self.inputModel.addEnabled = False
    self.inputModel.removeEnabled = False
    self.inputModel.noneEnabled = False
    self.inputModel.showHidden = False
    self.inputModel.showChildNodeTypes = False
    self.inputModel.setMRMLScene( slicer.mrmlScene )
    self.inputModel.setToolTip( "Pick the input model." )
    parametersFormLayout.addRow("Input Model: ", self.inputModel)

    #
    # Output Transform
    #
    self.outputTransform = slicer.qMRMLNodeComboBox()
    self.outputTransform.nodeTypes = ( ("vtkMRMLLinearTransformNode"), "" )
    self.outputTransform.selectNodeUponCreation = True
    self.outputTransform.addEnabled = True
    self.outputTransform.renameEnabled = True
    self.outputTransform.removeEnabled = True
    self.outputTransform.noneEnabled = False
    self.outputTransform.showHidden = False
    self.outputTransform.showChildNodeTypes = False
    self.outputTransform.setMRMLScene( slicer.mrmlScene )
    self.outputTransform.setToolTip( "Pick the output transform of the algorithm." )
    parametersFormLayout.addRow("Output Transform: ", self.outputTransform)

    #
    # Apply Button
    #
    self.applyButton = qt.QPushButton("Apply")
    self.applyButton.toolTip = "Run the algorithm."
    self.applyButton.enabled = False
    parametersFormLayout.addRow(self.applyButton)

    # connections
    self.placeSphereButton.connect('clicked(bool)', self.onPlaceSphereButton)
    self.sphereRadiusWidget.connect('valueChanged(double)', self.onSphereRadiusChanged)
    self.outputTransform.connect('currentNodeChanged(vtkMRMLNode*)', self.checkConditions)
    self.inputModel.connect('currentNodeChanged(vtkMRMLNode*)', self.checkConditions)
    self.applyButton.connect('clicked(bool)', self.onApplyButton)

    # variables
    self.sphereMarkupList = None
    self.sphereModel = None

    # Add vertical spacer
    self.layout.addStretch(1)

  def cleanup(self):
    pass

  def onPlaceSphereButton(self):
    if self.sphereMarkupList == None:
      print "No Markup List created yet. Creating one..."

      # Create new Markup node
      self.sphereMarkupList = slicer.mrmlScene.CreateNodeByClass('vtkMRMLMarkupsFiducialNode')
      self.sphereMarkupList.SetName("RobotPlacementSimulator-List")
      self.sphereMarkupList.SetMarkupLabelFormat("")
      slicer.mrmlScene.AddNode(self.sphereMarkupList)

      # Connect events
      self.sphereMarkupList.AddObserver(self.sphereMarkupList.PointModifiedEvent, self.onMarkupModified)
      self.sphereMarkupList.AddObserver(self.sphereMarkupList.MarkupRemovedEvent, self.onMarkupRemoved)

      print "Markup List created."
    
    # Switch Markups to Single Place Mode
    slicer.modules.markups.logic().SetActiveListID(self.sphereMarkupList)
    selectionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLSelectionNodeSingleton")
    selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")
    interactionNode = slicer.mrmlScene.GetNodeByID("vtkMRMLInteractionNodeSingleton")
    interactionNode.SwitchToSinglePlaceMode()

  @vtk.calldata_type(vtk.VTK_INT)
  def onMarkupModified(self, caller, eventID, callData):
    # New Markup added
    fiducialID = callData
    if fiducialID > 0:
      newPos = [0.0, 0.0, 0.0]
      caller.GetNthFiducialPosition(fiducialID, newPos)
      caller.SetNthFiducialPositionFromArray(0, newPos)
      caller.RemoveMarkup(fiducialID)
    
    # Markup Modified
    spherePosition = [0.0, 0.0, 0.0]
    caller.GetNthFiducialPosition(0, spherePosition)
    self.updateSphere(spherePosition, self.sphereRadiusWidget.value)

    self.checkConditions()

  @vtk.calldata_type(vtk.VTK_INT)
  def onMarkupRemoved(self, caller, eventID, callData):
    if caller.GetNumberOfMarkups() == 0:
      self.applyButton.enabled = False
      slicer.mrmlScene.RemoveNode(self.sphereModel)
      del self.sphereModel
      self.sphereModel = None

  def onSphereRadiusChanged(self, radius):
    spherePosition = [0.0, 0.0, 0.0]
    self.sphereMarkupList.GetNthFiducialPosition(0, spherePosition)
    self.updateSphere(spherePosition, radius)

  def updateSphere(self, position, radius):
    if self.sphereModel == None:
      # Create new model
      print "Creating new sphere model..."
      
      self.sphereModel = slicer.mrmlScene.CreateNodeByClass('vtkMRMLModelNode')
      self.sphereModel.SetName("RobotPlacementSimulatorModel")
      slicer.mrmlScene.AddNode(self.sphereModel)

      displayNode = slicer.mrmlScene.CreateNodeByClass('vtkMRMLModelDisplayNode')
      slicer.mrmlScene.AddNode(displayNode)
      displayNode.SetOpacity(0.35)
      displayNode.SetColor(1.0, 0.0, 0.0)
      self.sphereModel.SetAndObserveDisplayNodeID(displayNode.GetID())

      print "New model created"

    # Update model
    spherePolyData = vtk.vtkSphereSource()
    spherePolyData.SetCenter(position)
    spherePolyData.SetThetaResolution(20)
    spherePolyData.SetPhiResolution(20)
    spherePolyData.SetRadius(radius)
    spherePolyData.Update()

    self.sphereModel.SetAndObservePolyData(spherePolyData.GetOutput())
    self.sphereModel.Modified()

  def checkConditions(self):
    self.applyButton.enabled = self.sphereMarkupList.GetNumberOfMarkups() and self.outputTransform.currentNode() and self.inputModel.currentNode()

  def onApplyButton(self):
    logic = RobotPlacementSimulatorLogic()
    
    spherePosition = [0.0, 0.0, 0.0]
    self.sphereMarkupList.GetNthFiducialPosition(0, spherePosition)
    logic.run(self.inputModel.currentNode(), self.sphereModel, spherePosition, self.outputTransform.currentNode())

#
# RobotPlacementSimulatorLogic
#

class RobotPlacementSimulatorLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def isValidInputOutputData(self, inputModel, sphereModel, outputTransform):
    """Validates if the output is not the same as input
    """
    if not inputModel:
      logging.debug('isValidInputOutputData failed: no input model node defined')
      return False
    if not sphereModel:
      logging.debug('isValidInputOutputData failed: no sphere model node defined')
      return False
    if not outputTransform:
      logging.debug('isValidInputOutputData failed: no output transform node defined')
      return False      
    if inputModel.GetID()==sphereModel.GetID():
      logging.debug('isValidInputOutputData failed: input and sphere models are the same. Use a different input model.')
      return False
    return True

  def run(self, inputModel, sphereModel, spherePosition, outputTransform):
    """
    Run the actual algorithm
    """

    if not self.isValidInputOutputData(inputModel, sphereModel, outputTransform):
      slicer.util.errorDisplay('Input model is the same as sphere model. Choose a different input model.')
      return False

    logging.info('Processing started')

    # Convert sphere model to an implicit dataset to clip input model with it
    delaunay = vtk.vtkDelaunay3D()
    delaunay.SetInputData(sphereModel.GetPolyData())
    delaunay.Update()

    elevation = vtk.vtkElevationFilter()
    elevation.SetInputData(delaunay.GetOutput())
    elevation.Update();

    implicitDataSet = vtk.vtkImplicitDataSet()
    implicitDataSet.SetDataSet(elevation.GetOutput())

    # Clip and clean input model
    triangle = vtk.vtkTriangleFilter()
    triangle.SetInputData(inputModel.GetPolyData())
    triangle.Update()
    
    clip = vtk.vtkClipPolyData()
    clip.SetInputData(triangle.GetOutput())
    clip.SetClipFunction(implicitDataSet)
    clip.InsideOutOff()
    clip.Update()

    clean = vtk.vtkCleanPolyData()
    clean.SetInputConnection(clip.GetOutputPort())
    clean.Update()

    # Compute average normal
    clippedModel = clip.GetOutput()
    cellsNormal = clippedModel.GetPointData().GetNormals()
    
    averageNormal = [0.0, 0.0, 0.0]
    nOfNormals = 0;

    for cellIndex in range(0, cellsNormal.GetNumberOfTuples()):
      cellNormal = [0.0, 0.0, 0.0]
      cellsNormal.GetTuple(cellIndex, cellNormal)
      
      if not(math.isnan(cellNormal[0]) or math.isnan(cellNormal[1]) or math.isnan(cellNormal[2])):
        averageNormal[0] = averageNormal[0] + cellNormal[0]
        averageNormal[1] = averageNormal[1] + cellNormal[1]
        averageNormal[2] = averageNormal[2] + cellNormal[2]
        nOfNormals = nOfNormals + 1

    # Compute perpendicular vectors
    v1 = [0.0, 0.0, 0.0]
    v2 = [0.0, 0.0, 0.0]
    
    vtkmath = vtk.vtkMath()
    vtkmath.Perpendiculars(averageNormal, v2, v1, 0)

    # Normalize vectors
    vtkmath.Normalize(averageNormal)
    vtkmath.Normalize(v1)
    vtkmath.Normalize(v2)
    
    # Create Matrix4x4
    outputMatrix = vtk.vtkMatrix4x4()
    
    outputMatrix.SetElement(0,0,v1[0])
    outputMatrix.SetElement(1,0,v1[1])
    outputMatrix.SetElement(2,0,v1[2])
    outputMatrix.SetElement(3,0,0.0)

    outputMatrix.SetElement(0,1,averageNormal[0])
    outputMatrix.SetElement(1,1,averageNormal[1])
    outputMatrix.SetElement(2,1,averageNormal[2])
    outputMatrix.SetElement(3,1,0.0)

    outputMatrix.SetElement(0,2,v2[0])
    outputMatrix.SetElement(1,2,v2[1])
    outputMatrix.SetElement(2,2,v2[2])
    outputMatrix.SetElement(3,2,0.0)

    outputMatrix.SetElement(0,3,spherePosition[0])
    outputMatrix.SetElement(1,3,spherePosition[1])
    outputMatrix.SetElement(2,3,spherePosition[2])
    outputMatrix.SetElement(3,3,1.0)

    outputTransform.SetMatrixTransformToParent(outputMatrix)

    logging.info('Processing completed')

    return True


class RobotPlacementSimulatorTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_RobotPlacementSimulator1()

  def test_RobotPlacementSimulator1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")
    #
    # first, get some data
    #
    import urllib
    downloads = (
        ('http://slicer.kitware.com/midas3/download?items=5767', 'FA.nrrd', slicer.util.loadVolume),
        )

    for url,name,loader in downloads:
      filePath = slicer.app.temporaryPath + '/' + name
      if not os.path.exists(filePath) or os.stat(filePath).st_size == 0:
        logging.info('Requesting download %s from %s...\n' % (name, url))
        urllib.urlretrieve(url, filePath)
      if loader:
        logging.info('Loading %s...' % (name,))
        loader(filePath)
    self.delayDisplay('Finished with download and loading')

    volumeNode = slicer.util.getNode(pattern="FA")
    logic = RobotPlacementSimulatorLogic()
    self.assertTrue( logic.hasImageData(volumeNode) )
    self.delayDisplay('Test passed!')

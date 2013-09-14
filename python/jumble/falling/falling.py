#============================================================================
#
#              Test of the Robot Falling Down
#
#============================================================================

from dynamic_graph.sot.core import *
from dynamic_graph.sot.dynamics import *
from dynamic_graph.sot.dyninv import *
from dynamic_graph.sot.oscar import SolverMotionReduced
from dynamic_graph.script_shortcuts import optionalparentheses
from dynamic_graph import plug

from dynamic_graph.sot.core.utils.viewer_helper import addRobotViewer,VisualPinger
from dynamic_graph.sot.core.utils.thread_interruptible_loop import *
from dynamic_graph.sot.core.utils.attime import attime

from dynamic_graph.sot.dyninv.robot_specific import pkgDataRootDir, modelName, robotDimension, initialConfig, gearRatio, inertiaRotor
from dynamic_graph.sot.dyninv.meta_task_dyn_6d import MetaTaskDyn6d
from dynamic_graph.sot.dyninv.meta_tasks_dyn import MetaTaskDynCom, MetaTaskDynPosture, MetaTaskDynLimits, AddContactHelper, gotoNd

from numpy import *


initialConfig['hrp14small'] = ( 0,0,0.6487,0,0,0,0,0,-0.453786,0.872665,-0.418879,0,0,0,-0.453786,0.872665,-0.418879,0,0,0,0,0,0.261799,-0.174533,0,-0.523599,0,0,0.174533,0.261799,0.174533,0,-0.523599,0,0,0.174533 )


# ------------------------------------------------------------------------------
# --- ROBOT DYNAMIC SIMULATION -------------------------------------------------
# ------------------------------------------------------------------------------

robotName = 'hrp14small'
robotDim   = robotDimension[robotName]
RobotClass = RobotDynSimu
robot      = RobotClass("robot")
robot.resize(robotDim)
robot.set( initialConfig[robotName] )

addRobotViewer(robot,small=True,verbose=False)

dt=5e-3

# ------------------------------------------------------------------------------
# --- MAIN LOOP ----------------------------------------------------------------
# ------------------------------------------------------------------------------

def inc():
    robot.increment(dt)
    attime.run(robot.control.time)
    # verif.record()

    if dyn.com.time >0:
        robot.viewer.updateElementConfig('com',[dyn.com.value[0],dyn.com.value[1],0,0,0,0])


@loopInThread
def loop():
    inc()
runner=loop()

@optionalparentheses
def go(): runner.play()
@optionalparentheses
def stop(): runner.pause()
@optionalparentheses
def next(): inc()

# --- shortcuts -------------------------------------------------
@optionalparentheses
def q():
    print robot.state.__repr__()
@optionalparentheses
def qdot(): print robot.control.__repr__()
@optionalparentheses
def iter():         print 'iter = ',robot.state.time
@optionalparentheses
def status():       print runner.isPlay

#-----------------------------------------------------------------------------
#---- DYN --------------------------------------------------------------------
#-----------------------------------------------------------------------------

modelDir          = pkgDataRootDir[robotName]
xmlDir            = pkgDataRootDir[robotName]
specificitiesPath = xmlDir + '/HRP2SpecificitiesSmall.xml'
jointRankPath     = xmlDir + '/HRP2LinkJointRankSmall.xml'

dyn = Dynamic("dyn")
dyn.setFiles(modelDir,modelName[robotName],specificitiesPath,jointRankPath)
dyn.parse()

dyn.inertiaRotor.value = inertiaRotor[robotName]
dyn.gearRatio.value    = gearRatio[robotName]

plug(robot.state,dyn.position)
plug(robot.velocity,dyn.velocity)
dyn.acceleration.value = robotDim*(0.,)

dyn.ffposition.unplug()
dyn.ffvelocity.unplug()
dyn.ffacceleration.unplug()

dyn.setProperty('ComputeBackwardDynamics','true')
dyn.setProperty('ComputeAccelerationCoM','true')

robot.control.unplug()

#-----------------------------------------------------------------------------
# --- OPERATIONAL TASKS (For HRP2-14)-----------------------------------------
#-----------------------------------------------------------------------------

taskWaist = MetaTaskDyn6d('taskWaist', dyn, 'waist', 'waist')
taskChest = MetaTaskDyn6d('taskChest', dyn, 'chest', 'chest')
taskHead  = MetaTaskDyn6d('taskHead', dyn, 'head', 'gaze')
taskrh    = MetaTaskDyn6d('rh', dyn, 'rh', 'right-wrist')
tasklh    = MetaTaskDyn6d('lh', dyn, 'lh', 'left-wrist')

for task in [ taskWaist, taskChest, taskHead, taskrh, tasklh]:
    task.feature.frame('current')
    task.gain.setConstant(50)
    task.task.dt.value = dt
    # ADDED TO AVOID ERRORS: VERIFY IF THERE IS A BETTER WAY!!!
    task.featureDes.velocity.value=(0,0,0,0,0,0)

# CoM Task
taskCom = MetaTaskDynCom(dyn,dt)

# Posture Task
taskPosture = MetaTaskDynPosture(dyn,dt)

# Inequality Task for the CoM
class MetaTaskDynInequality:
    pass
taskComIneq = MetaTaskDynInequality()

# taskComIneq.feature    = FeatureGeneric('featureComInequality')
# taskComIneq.featureDes = FeatureGeneric('featureDesComInequality')
# taskComIneq.task = TaskDynInequality('taskComInequality')
# taskComIneq.gain = GainAdaptive('gaintaskComInequality')
# plug(dyn.com, taskComIneq.feature.errorIN)
# plug(dyn.Jcom, taskComIneq.feature.jacobianIN)
# taskComIneq.feature.setReference(taskComIneq.featureDes.name)
# taskComIneq.task.add(taskComIneq.feature.name)
# plug(dyn.velocity, taskComIneq.task.qdot)
# taskComIneq.task.dt.value = dt
# plug(taskComIneq.task.error, taskComIneq.gain.error)
# plug(taskComIneq.gain.gain, taskComIneq.task.controlGain)

# taskComIneq.task.referenceInf.value = (0.13,)     # Xmin, Ymin
# taskComIneq.task.referenceSup.value = (-0.08,)    # Xmin, Ymin
# taskComIneq.featureDes.errorIN.value = (0,)
# taskComIneq.feature.selec.value = "001"

taskComIneq = MetaTaskDynCom(dyn,dt,name="comIneq")
taskComIneq.task = TaskDynInequality('taskComInequality')
taskComIneq.task.add(taskComIneq.feature.name)
taskComIneq.task.dt.value = dt
plug(dyn.velocity, taskComIneq.task.qdot)

taskComIneq.feature.selec.value = "001"
taskComIneq.featureDes.errorIN.value = (0,)
taskComIneq.task.referenceInf.value = (-0.08,)     # Xmin, Ymin
taskComIneq.task.referenceSup.value = (0.13,)    # Xmin, Ymin

# #taskComIneq.task.controlGain.value = 0.9



# Angular position and velocity limits
taskLim = MetaTaskDynLimits(dyn,dt)
# taskLim = TaskDynLimits('taskLim')
# plug(dyn.position,taskLim.position)
# plug(dyn.velocity,taskLim.velocity)
# taskLim.dt.value = dt

# dyn.upperJl.recompute(0)
# dyn.lowerJl.recompute(0)
# taskLim.referencePosInf.value = dyn.lowerJl.value
# taskLim.referencePosSup.value = dyn.upperJl.value

# #dqup = (0, 0, 0, 0, 0, 0, 200, 220, 250, 230, 290, 520, 200, 220, 250, 230, 290, 520, 250, 140, 390, 390, 240, 140, 240, 130, 270, 180, 330, 240, 140, 240, 130, 270, 180, 330)
# dqup = (1000,)*robotDim
# taskLim.referenceVelInf.value = tuple([-val*pi/180 for val in dqup])
# taskLim.referenceVelSup.value = tuple([ val*pi/180 for val in dqup])


#-----------------------------------------------------------------------------
# --- Stack of tasks controller  ---------------------------------------------
#-----------------------------------------------------------------------------

#sot    = SolverDynReduced('sot')
sot     = SolverMotionReduced('sot')
contact = AddContactHelper(sot)

sot.setSize(robotDim-6)
sot.breakFactor.value = 10

plug(dyn.inertiaReal,sot.matrixInertia)
plug(dyn.dynamicDrift,sot.dyndrift)
plug(dyn.velocity,sot.velocity)

plug(sot.solution, robot.control)
plug(sot.acceleration,robot.acceleration)


#-----------------------------------------------------------------------------
# ---- CONTACT: Contact definition -------------------------------------------
#-----------------------------------------------------------------------------

# Left foot contact
contactLF = MetaTaskDyn6d('contact_lleg',dyn,'lf','left-ankle')
contactLF.feature.frame('desired')
contactLF.name = "LF"

# Right foot contact
contactRF = MetaTaskDyn6d('contact_rleg',dyn,'rf','right-ankle')
contactRF.feature.frame('desired')
contactRF.name = "RF"

contactRF.support = ((0.11,-0.08,-0.08,0.11),(-0.045,-0.045,0.07,0.07),(-0.105,-0.105,-0.105,-0.105))
contactLF.support = ((0.11,-0.08,-0.08,0.11),(-0.07,-0.07,0.045,0.045),(-0.105,-0.105,-0.105,-0.105))
contactLF.support =  ((0.03,-0.03,-0.03,0.03),(-0.015,-0.015,0.015,0.015),(-0.105,-0.105,-0.105,-0.105))

# For velocities
contactLF.featureDes.velocity.value=(0,0,0,0,0,0)
contactRF.featureDes.velocity.value=(0,0,0,0,0,0)

# Imposed erordot = 0 : is there a better alternative ???
contactLF.feature.errordot.value=(0,0,0,0,0,0)
contactRF.feature.errordot.value=(0,0,0,0,0,0)



#-----------------------------------------------------------------------------
# --- TRACE ------------------------------------------------------------------
#-----------------------------------------------------------------------------

from dynamic_graph.tracer import *
tr = Tracer('tr')
tr.open('/tmp/','testM_','.dat')

tr.add('sot.acceleration','')
tr.add('sot.torque','')
tr.add('sot.reducedControl','')
tr.add('sot.reducedForce','')
tr.add('sot.forces','')
tr.add('sot.forcesNormal','')
tr.add('sot.reducedForce','')
tr.start()

robot.after.addSignal('sot.reducedForce')
robot.after.addSignal('sot.forces')
robot.after.addSignal('sot.torque')

robot.after.addSignal('tr.triger')
robot.after.addSignal(contactLF.task.name+'.error')
robot.after.addSignal('dyn.rf')
robot.after.addSignal('dyn.lf')
robot.after.addSignal('dyn.chest')
robot.after.addSignal('dyn.com')
robot.after.addSignal('sot.forcesNormal')
robot.after.addSignal('dyn.waist')

robot.after.addSignal(taskLim.task.name+'.normalizedPosition')


#-----------------------------------------------------------------------------
# --- RUN --------------------------------------------------------------------
#-----------------------------------------------------------------------------

sot.clear()
contact(contactLF)
contact(contactRF)
''' To avoid problems with solverMotionReduced '''
if (cmp(sot.className,'SolverMotionReduced')==0):
    sot._RF_ddx3.value = ((0.,0.,0.,),)
    sot._LF_ddx3.value = ((0.,0.,0.,),)

sot.push(taskLim.task.name)
plug(robot.state,sot.position)

q0 = robot.state.value
chest0 = matrix(dyn.chest.value)[0:3,3]

taskCom.feature.selec.value = "11"
#taskCom.gain.setByPoint(100,10,0.005,0.8)
taskCom.gain.setConstant(1)

r = radians
sigset = ( lambda s, v : s.__class__.value.__set__(s,v) )
refset = ( lambda mt,v : mt.__class__.ref.__set__(mt,v) )

# # Abusive way to overcontrol the CoM (creates problems with control)
# attime(2 ,(lambda: sot.push(taskCom.task.name),"Add CoM")
#          ,(lambda: refset(taskCom, ( 0.014, 0.001,  0.8 )), "Com to left foot")
#        )

# Controlling the CoM in inequality
attime( 2
        ,(lambda: sot.push(taskComIneq.task.name),"Add CoM")
        )


# Task trying to make the robot fall
taskChest.feature.frame('desired')
attime(3 ,
       (lambda: sot.push(taskChest.task.name), "Add Chest"),
       (lambda: gotoNd(taskChest, (0.3, 0, 0), "000001", gain=(1.0,)), "Move chest forward"),
       )

attime(1000, stop, "Stopped")

go()
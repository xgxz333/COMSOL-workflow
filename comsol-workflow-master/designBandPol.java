/*
 * designBandPol.java
 */

import com.comsol.model.*;
import com.comsol.model.util.*;

/** Model exported on Mar 27 2026, 14:31 by COMSOL 6.3.0.290. */
public class designBandPol {

  public static Model run() {
    Model model = ModelUtil.create("Model");

    model.modelPath("C:\\Users\\DELL\\Desktop\\Shaolei");

    model.label("design_band.mph");

    model.param().set("a", "0.82 [um]");
    model.param().set("H", "200 [nm]");
    model.param().set("H_air", "lda0");
    model.param().set("lda0", "1550 [nm]");
    model.param().set("G", "4*pi/sqrt(3)/a");
    model.param().set("kx", "0*G");
    model.param().set("ky", "0*G");
    model.param().label("Parameters 1");

    model.component().create("comp1", true);

    model.component("comp1").geom().create("geom1", 3);

    model.component("comp1").label("Component 1");

    model.result().table().create("tbl1", "Table");
    model.result().table().create("tbl2", "Table");
    model.result().table().create("tbl3", "Table");
    model.result().table().create("tbl4", "Table");
    model.result().table().create("tbl5", "Table");
    model.result().table().create("tbl6", "Table");

    model.component("comp1").mesh().create("mesh1");

    model.component("comp1").geom("geom1").label("Geometry 1");
    model.component("comp1").geom("geom1").lengthUnit("\u00b5m");
    model.component("comp1").geom("geom1").geomRep("cadps");
    model.component("comp1").geom("geom1").designBooleans(true);
    model.component("comp1").geom("geom1").create("wp1", "WorkPlane");
    model.component("comp1").geom("geom1").feature("wp1").label("Work Plane 1");
    model.component("comp1").geom("geom1").feature("wp1").set("unite", true);
    model.component("comp1").geom("geom1").feature("wp1").geom().label("Plane Geometry");
    model.component("comp1").geom("geom1").feature("wp1").geom().create("pol1", "Polygon");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol1").label("Hex");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol1").set("source", "table");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol1")
         .set("table", new String[][]{{"a/sqrt(3)*cos(pi/6)", "a/sqrt(3)*sin(pi/6)"}, 
         {"0", "a/sqrt(3)"}, 
         {"-a/sqrt(3)*cos(pi/6)", "a/sqrt(3)*sin(pi/6)"}, 
         {"-a/sqrt(3)*cos(pi/6)", "-a/sqrt(3)*sin(pi/6)"}, 
         {"0", "-a/sqrt(3)"}, 
         {"a/sqrt(3)*cos(pi/6)", "-a/sqrt(3)*sin(pi/6)"}});
    model.component("comp1").geom("geom1").feature("wp1").geom().create("pol2", "Polygon");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol2").label("Tri_1");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol2").set("source", "table");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol2")
         .set("table", new String[][]{{"0.21225765765495208 [um]", "0.0 [um]"}, {"0.3901101748389039 [um]", "-0.10268319867220715 [um]"}, {"0.3901101748389039 [um]", "0.10268319867220715 [um]"}});
    model.component("comp1").geom("geom1").feature("wp1").geom().create("pol3", "Polygon");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol3").label("Tri_2");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol3").set("source", "table");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol3")
         .set("table", new String[][]{{"0.05275932699428607 [um]", "0.09138183492724362 [um]"}, {"0.23061184417823793 [um]", "0.19406503359945076 [um]"}, {"0.052759326994286086 [um]", "0.2967482322716579 [um]"}});
    model.component("comp1").geom("geom1").feature("wp1").geom().create("pol4", "Polygon");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol4").label("Tri_3");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol4").set("source", "table");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol4")
         .set("table", new String[][]{{"-0.05275932699428601 [um]", "0.0913818349272436 [um]"}, {"-0.05275932699428596 [um]", "0.29674823227165786 [um]"}, {"-0.23061184417823785 [um]", "0.19406503359945076 [um]"}});
    model.component("comp1").geom("geom1").feature("wp1").geom().create("pol5", "Polygon");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol5").label("Tri_4");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol5").set("source", "table");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol5")
         .set("table", new String[][]{{"-0.21225765765495208 [um]", "2.5994066104165176e-17 [um]"}, {"-0.3901101748389039 [um]", "0.1026831986722072 [um]"}, {"-0.3901101748389039 [um]", "-0.10268319867220711 [um]"}});
    model.component("comp1").geom("geom1").feature("wp1").geom().create("pol6", "Polygon");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol6").label("Tri_5");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol6").set("source", "table");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol6")
         .set("table", new String[][]{{"-0.052759326994286135 [um]", "-0.09138183492724365 [um]"}, {"-0.23061184417823807 [um]", "-0.19406503359945068 [um]"}, {"-0.052759326994286246 [um]", "-0.2967482322716579 [um]"}});
    model.component("comp1").geom("geom1").feature("wp1").geom().create("pol7", "Polygon");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol7").label("Tri_6");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol7").set("source", "table");
    model.component("comp1").geom("geom1").feature("wp1").geom().feature("pol7")
         .set("table", new String[][]{{"0.05275932699428607 [um]", "-0.09138183492724362 [um]"}, {"0.052759326994286086 [um]", "-0.2967482322716579 [um]"}, {"0.23061184417823793 [um]", "-0.19406503359945076 [um]"}});
    model.component("comp1").geom("geom1").create("ext1", "Extrude");
    model.component("comp1").geom("geom1").feature("ext1").label("Extrude 1");
    model.component("comp1").geom("geom1").feature("ext1").setIndex("distance", "H/2", 0);
    model.component("comp1").geom("geom1").feature("ext1").selection("input").set("wp1");
    model.component("comp1").geom("geom1").create("wp2", "WorkPlane");
    model.component("comp1").geom("geom1").feature("wp2").label("Work Plane 2");
    model.component("comp1").geom("geom1").feature("wp2").set("quickz", "H/2");
    model.component("comp1").geom("geom1").feature("wp2").set("unite", true);
    model.component("comp1").geom("geom1").feature("wp2").geom().label("Plane Geometry");
    model.component("comp1").geom("geom1").feature("wp2").geom().create("pol8", "Polygon");
    model.component("comp1").geom("geom1").feature("wp2").geom().feature("pol8").label("Hex 1");
    model.component("comp1").geom("geom1").feature("wp2").geom().feature("pol8").set("source", "table");
    model.component("comp1").geom("geom1").feature("wp2").geom().feature("pol8")
         .set("table", new String[][]{{"a/sqrt(3)*cos(pi/6)", "a/sqrt(3)*sin(pi/6)"}, 
         {"0", "a/sqrt(3)"}, 
         {"-a/sqrt(3)*cos(pi/6)", "a/sqrt(3)*sin(pi/6)"}, 
         {"-a/sqrt(3)*cos(pi/6)", "-a/sqrt(3)*sin(pi/6)"}, 
         {"0", "-a/sqrt(3)"}, 
         {"a/sqrt(3)*cos(pi/6)", "-a/sqrt(3)*sin(pi/6)"}});
    model.component("comp1").geom("geom1").create("ext2", "Extrude");
    model.component("comp1").geom("geom1").feature("ext2").label("Extrude 2");
    model.component("comp1").geom("geom1").feature("ext2").set("distance", new String[]{"H_air", "H_air*1.5"});
    model.component("comp1").geom("geom1").feature("ext2").set("scale", new double[][]{{1, 1}, {1, 1}});
    model.component("comp1").geom("geom1").feature("ext2").set("displ", new double[][]{{0, 0}, {0, 0}});
    model.component("comp1").geom("geom1").feature("ext2").set("twist", new int[]{0, 0});
    model.component("comp1").geom("geom1").feature("ext2").selection("input").set("wp2");
    model.component("comp1").geom("geom1").feature("fin").label("Form Union");
    model.component("comp1").geom("geom1").run();

    model.component("comp1").selection().create("sel1", "Explicit");
    model.component("comp1").selection("sel1").geom("geom1", 2);
    model.component("comp1").selection("sel1").set(3, 16, 21, 25, 37, 42, 47);
    model.component("comp1").selection("sel1").label("bottom");
    model.component("comp1").selection("sel1").set("groupcontang", true);

    model.view().create("view4", 2);

    model.component("comp1").material().create("mat1", "Common");
    model.component("comp1").material().create("mat2", "Common");
    model.component("comp1").material("mat1").propertyGroup()
         .create("RefractiveIndex", "RefractiveIndex", "Refractive index");
    model.component("comp1").material("mat2").selection().set(1);
    model.component("comp1").material("mat2").propertyGroup()
         .create("RefractiveIndex", "RefractiveIndex", "Refractive index");

    model.component("comp1").cpl().create("intop1", "Integration");
    model.component("comp1").cpl("intop1").selection().named("sel1");

    model.component("comp1").coordSystem().create("pml1", "PML");
    model.component("comp1").coordSystem("pml1").selection().set(3);

    model.component("comp1").physics().create("ewfd", "ElectromagneticWavesFrequencyDomain", "geom1");
    model.component("comp1").physics("ewfd").create("sctr1", "Scattering", 2);
    model.component("comp1").physics("ewfd").feature("sctr1").selection().set(10);
    model.component("comp1").physics("ewfd").create("pmc1", "PerfectMagneticConductor", 2);
    model.component("comp1").physics("ewfd").feature("pmc1").selection().named("sel1");
    model.component("comp1").physics("ewfd").create("pc1", "PeriodicCondition", 2);
    model.component("comp1").physics("ewfd").feature("pc1").selection().set(2, 5, 8, 32, 33, 34);
    model.component("comp1").physics("ewfd").create("pc2", "PeriodicCondition", 2);
    model.component("comp1").physics("ewfd").feature("pc2").selection().set(11, 12, 13, 29, 30, 31);
    model.component("comp1").physics("ewfd").create("pc3", "PeriodicCondition", 2);
    model.component("comp1").physics("ewfd").feature("pc3").selection().set(1, 4, 7, 50, 51, 52);

    model.result().table("tbl1").label("Table 1");
    model.result().table("tbl3").comments("band");
    model.result().table("tbl4").comments("Q");
    model.result().table("tbl6").comments("\u8868\u9762\u79ef\u5206 1");

    model.thermodynamics().label("Thermodynamics");

    model.component("comp1").view("view1").label("View 1");
    model.component("comp1").view("view1").set("renderwireframe", true);
    model.component("comp1").view("view1").set("scenelight", false);
    model.component("comp1").view("view1").axis().label("Axis");
    model.component("comp1").view("view1").light("lgt1").label("Directional Light 1");
    model.component("comp1").view("view1").light("lgt2").label("Directional Light 2");
    model.component("comp1").view("view1").light("lgt3").label("Directional Light 3");
    model.component("comp1").view("view2").label("View 2");
    model.component("comp1").view("view2").axis().label("Axis");
    model.component("comp1").view("view2").axis().set("xmin", -0.7867843508720398);
    model.component("comp1").view("view2").axis().set("xmax", 0.830589234828949);
    model.component("comp1").view("view2").axis().set("ymin", -0.6027438640594482);
    model.component("comp1").view("view2").axis().set("ymax", 0.7357029914855957);
    model.component("comp1").view("view3").label("View 3");
    model.component("comp1").view("view3").axis().label("Axis");
    model.component("comp1").view("view3").axis().set("xmin", -6.29296152965253E-7);
    model.component("comp1").view("view3").axis().set("xmax", 6.29296152965253E-7);
    model.component("comp1").view("view3").axis().set("ymin", -5.207699018683343E-7);
    model.component("comp1").view("view3").axis().set("ymax", 5.207699018683343E-7);
    model.view("view4").label("View 2D 4");
    model.view("view4").axis().label("Axis");
    model.view("view4").axis().set("xmin", -0.6187745928764343);
    model.view("view4").axis().set("xmax", 0.6187745928764343);
    model.view("view4").axis().set("ymin", -0.5207698941230774);
    model.view("view4").axis().set("ymax", 0.5207698941230774);

    model.material().label("Materials");
    model.component("comp1").material("mat1").label("AIr");
    model.component("comp1").material("mat1").propertyGroup("def").label("Basic");
    model.component("comp1").material("mat1").propertyGroup("RefractiveIndex").label("Refractive index");
    model.component("comp1").material("mat1").propertyGroup("RefractiveIndex").info("category").label("Information");
    model.component("comp1").material("mat1").propertyGroup("RefractiveIndex")
         .set("n", new String[]{"1", "0", "0", "0", "1", "0", "0", "0", "1"});
    model.component("comp1").material("mat2").label("Mat");
    model.component("comp1").material("mat2").propertyGroup("def").label("Basic");
    model.component("comp1").material("mat2").propertyGroup("RefractiveIndex").label("Refractive index");
    model.component("comp1").material("mat2").propertyGroup("RefractiveIndex").info("category").label("Information");
    model.component("comp1").material("mat2").propertyGroup("RefractiveIndex")
         .set("n", new String[]{"3.3", "0", "0", "0", "3.3", "0", "0", "0", "3.3"});

    model.component("comp1").coordSystem("sys1").label("Boundary System 1");
    model.component("comp1").coordSystem("pml1").label("Perfectly Matched Layer 1");

    model.common("cminpt").label("Default Model Inputs");

    model.component("comp1").physics("ewfd").label("Electromagnetic Waves, Frequency Domain");
    model.component("comp1").physics("ewfd").feature("wee1")
         .set("multiphysics", "The Semiconductor Electromagnetic Waves multiphysics coupling adds additional contributions to the optical properties");
    model.component("comp1").physics("ewfd").feature("wee1").label("Wave Equation, Electric 1");
    model.component("comp1").physics("ewfd").feature("wee1").featureInfo("info").label("Equation View");
    model.component("comp1").physics("ewfd").feature("pec1").label("Perfect Electric Conductor 1");
    model.component("comp1").physics("ewfd").feature("pec1").featureInfo("info").label("Equation View");
    model.component("comp1").physics("ewfd").feature("init1").label("Initial Values 1");
    model.component("comp1").physics("ewfd").feature("init1").featureInfo("info").label("Equation View");
    model.component("comp1").physics("ewfd").feature("dcont1").label("Continuity 1");
    model.component("comp1").physics("ewfd").feature("dcont1").featureInfo("info").label("Equation View");
    model.component("comp1").physics("ewfd").feature("sctr1").label("Scattering Boundary Condition 1");
    model.component("comp1").physics("ewfd").feature("sctr1").featureInfo("info").label("Equation View");
    model.component("comp1").physics("ewfd").feature("pmc1").label("Perfect Magnetic Conductor 1");
    model.component("comp1").physics("ewfd").feature("pmc1").featureInfo("info").label("Equation View");
    model.component("comp1").physics("ewfd").feature("pc1").set("PeriodicType", "Floquet");
    model.component("comp1").physics("ewfd").feature("pc1").set("kFloquet", new String[][]{{"kx"}, {"ky"}, {"0"}});
    model.component("comp1").physics("ewfd").feature("pc1").label("Periodic Condition 1");
    model.component("comp1").physics("ewfd").feature("pc1").featureInfo("info").label("Equation View");
    model.component("comp1").physics("ewfd").feature("pc2").set("PeriodicType", "Floquet");
    model.component("comp1").physics("ewfd").feature("pc2").set("kFloquet", new String[][]{{"kx"}, {"ky"}, {"0"}});
    model.component("comp1").physics("ewfd").feature("pc2").label("Periodic Condition 2");
    model.component("comp1").physics("ewfd").feature("pc2").featureInfo("info").label("Equation View");
    model.component("comp1").physics("ewfd").feature("pc3").set("PeriodicType", "Floquet");
    model.component("comp1").physics("ewfd").feature("pc3").set("kFloquet", new String[][]{{"kx"}, {"ky"}, {"0"}});
    model.component("comp1").physics("ewfd").feature("pc3").label("Periodic Condition 3");
    model.component("comp1").physics("ewfd").feature("pc3").featureInfo("info").label("Equation View");

    model.component("comp1").mesh("mesh1").label("Mesh 1");

    model.study().create("std1");
    model.study("std1").create("param", "Parametric");
    model.study("std1").create("eig", "Eigenfrequency");

    model.sol().create("sol1");
    model.sol("sol1").attach("std1");
    model.sol().create("sol2");
    model.sol("sol2").study("std1");
    model.sol("sol2").label("\u53c2\u6570\u5316\u89e3 1");

    model.result().dataset().create("cpl1", "CutPlane");
    model.result().numerical().create("gev1", "EvalGlobal");
    model.result().create("pg1", "PlotGroup2D");
    model.result("pg1").create("surf1", "Surface");
    model.result("pg1").feature("surf1").set("expr", "ewfd.normH");
    model.result().export().create("plot1", "Plot");
    model.result().export().create("img1", "Image");
    model.result().export().create("img2", "Image");

    model.study("std1").label("Study 1");
    model.study("std1").feature("param").set("pname", new String[]{"kx", "ky"});
    model.study("std1").feature("param").set("plistarr", new int[]{0, 0});
    model.study("std1").feature("param").set("punit", new String[]{"1/um", "1/um"});
    model.study("std1").feature("eig").label("Eigenfrequency");
    model.study("std1").feature("eig").set("neigs", 4);
    model.study("std1").feature("eig").set("neigsactive", true);
    model.study("std1").feature("eig").set("shift", "c_const/1.55[um]");
    model.study("std1").feature("eig").set("filtereigdescription", new String[]{"Damped natural frequency"});

    model.batch().label("Batch");

    model.study("std1").createAutoSequences("jobs");

    model.batch("p1").feature("so1").set("psol", "sol2");

    model.sol("sol1").createAutoSequence("std1");
    model.sol("sol1").label("Solution 1");

    model.study("std1").runNoGen();

    model.result().label("Results");
    model.result().dataset("cpl1").label("Cut Plane 1");
    model.result().dataset("cpl1").set("quickplane", "xy");
    model.result().numerical("gev1").label("Eigenfrequencies (ewfd)");
    model.result().numerical("gev1").set("table", "tbl1");
    model.result().numerical("gev1")
         .set("expr", new String[]{"ewfd.freq", "ewfd.Qfactor", "intop1(ewfd.Ex*exp(i*kx*x+i*ky*y))/intop1(1)", "intop1(ewfd.Ey*exp(i*kx*x+i*ky*y))/intop1(1)"});
    model.result().numerical("gev1").set("unit", new String[]{"THz", "1", "V/m", "V*m"});
    model.result().numerical("gev1").set("descr", new String[]{"Frequency", "Quality factor", "cx(k)", "cy(k)"});
    model.result().numerical("gev1").setResult();
    model.result("pg1").label("2D Field (ewfd)");
    model.result("pg1").set("looplevel", new int[]{4});
    model.result("pg1").feature("surf1").label("Surface 1");
    model.result("pg1").feature("surf1").set("resolution", "normal");
    model.result().export("plot1").label("Plot 1");
    model.result().export("img1").label("Image 1");
    model.result().export("img1").set("sourceobject", "pg1");
    model.result().export("img1").set("size", "current");
    model.result().export("img1").set("zoomextents", "off");
    model.result().export("img1").set("antialias", "on");
    model.result().export("img1").set("options1d", "on");
    model.result().export("img1").set("options2d", "on");
    model.result().export("img1").set("options3d", "on");
    model.result().export("img1").set("title1d", "on");
    model.result().export("img1").set("title2d", "off");
    model.result().export("img1").set("title3d", "off");
    model.result().export("img1").set("legend1d", "on");
    model.result().export("img1").set("legend2d", "off");
    model.result().export("img1").set("legend3d", "on");
    model.result().export("img1").set("axes1d", "on");
    model.result().export("img1").set("axes2d", "off");
    model.result().export("img1").set("logo1d", "on");
    model.result().export("img1").set("logo2d", "off");
    model.result().export("img1").set("logo3d", "off");
    model.result().export("img1").set("showgrid", "on");
    model.result().export("img1").set("axisorientation", "off");
    model.result().export("img1").set("grid", "off");
    model.result().export("img1").set("fontsize", "9");
    model.result().export("img1").set("colortheme", "globaltheme");
    model.result().export("img1").set("background", "color");
    model.result().export("img1").set("gltfincludelines", "on");
    model.result().export("img1").set("qualitylevel", "100");
    model.result().export("img1").set("qualityactive", "on");
    model.result().export("img1").set("imagetype", "png");
    model.result().export("img1").set("target", "file");
    model.result().export("img1").set("addsuffix", "off");
    model.result().export("img1").set("lockview", "off");
    model.result().export("img1").set("customcolor", new double[]{1, 1, 1});
    model.result().export("img1").set("options2d", true);
    model.result().export("img1").set("fontsize", 9);
    model.result().export("img1").set("background", "color");
    model.result().export("img1").set("title2d", true);
    model.result().export("img1").set("legend2d", true);
    model.result().export("img1").set("axes2d", true);
    model.result().export("img1").set("logo2d", true);
    model.result().export("img1").set("logo3d", true);
    model.result().export("img1").set("size", "current");
    model.result().export("img1").set("unit", "px");
    model.result().export("img1").set("height", "656");
    model.result().export("img1").set("width", "874");
    model.result().export("img1").set("lockratio", "off");
    model.result().export("img1").set("resolution", "500");
    model.result().export("img1").set("antialias", "on");
    model.result().export("img1").set("zoomextents", "off");
    model.result().export("img1").set("fontsize", "9");
    model.result().export("img1").set("colortheme", "globaltheme");
    model.result().export("img1").set("customcolor", new double[]{1, 1, 1});
    model.result().export("img1").set("background", "color");
    model.result().export("img1").set("gltfincludelines", "on");
    model.result().export("img1").set("title1d", "on");
    model.result().export("img1").set("legend1d", "on");
    model.result().export("img1").set("logo1d", "on");
    model.result().export("img1").set("options1d", "on");
    model.result().export("img1").set("title2d", "on");
    model.result().export("img1").set("legend2d", "on");
    model.result().export("img1").set("logo2d", "on");
    model.result().export("img1").set("options2d", "on");
    model.result().export("img1").set("title3d", "off");
    model.result().export("img1").set("legend3d", "on");
    model.result().export("img1").set("logo3d", "on");
    model.result().export("img1").set("options3d", "on");
    model.result().export("img1").set("axisorientation", "off");
    model.result().export("img1").set("grid", "off");
    model.result().export("img1").set("axes1d", "on");
    model.result().export("img1").set("axes2d", "on");
    model.result().export("img1").set("showgrid", "on");
    model.result().export("img1").set("target", "file");
    model.result().export("img1").set("qualitylevel", "100");
    model.result().export("img1").set("qualityactive", "on");
    model.result().export("img1").set("imagetype", "png");
    model.result().export("img1").set("lockview", "off");
    model.result().export("img2").label("Image 2");
    model.result().export("img2").set("size", "current");
    model.result().export("img2").set("zoomextents", "off");
    model.result().export("img2").set("antialias", "on");
    model.result().export("img2").set("options1d", "on");
    model.result().export("img2").set("options2d", "on");
    model.result().export("img2").set("options3d", "on");
    model.result().export("img2").set("title1d", "on");
    model.result().export("img2").set("title2d", "off");
    model.result().export("img2").set("title3d", "off");
    model.result().export("img2").set("legend1d", "on");
    model.result().export("img2").set("legend2d", "off");
    model.result().export("img2").set("legend3d", "on");
    model.result().export("img2").set("axes1d", "on");
    model.result().export("img2").set("axes2d", "off");
    model.result().export("img2").set("logo1d", "on");
    model.result().export("img2").set("logo2d", "off");
    model.result().export("img2").set("logo3d", "off");
    model.result().export("img2").set("showgrid", "on");
    model.result().export("img2").set("axisorientation", "off");
    model.result().export("img2").set("grid", "off");
    model.result().export("img2").set("fontsize", "9");
    model.result().export("img2").set("colortheme", "globaltheme");
    model.result().export("img2").set("background", "color");
    model.result().export("img2").set("gltfincludelines", "on");
    model.result().export("img2").set("qualitylevel", "100");
    model.result().export("img2").set("qualityactive", "on");
    model.result().export("img2").set("imagetype", "png");
    model.result().export("img2").set("target", "file");
    model.result().export("img2").set("addsuffix", "off");
    model.result().export("img2").set("lockview", "off");
    model.result().export("img2").set("customcolor", new double[]{1, 1, 1});
    model.result().export("img2").set("options3d", true);
    model.result().export("img2").set("fontsize", 9);
    model.result().export("img2").set("background", "color");
    model.result().export("img2").set("logo2d", true);
    model.result().export("img2").set("title3d", true);
    model.result().export("img2").set("grid", true);
    model.result().export("img2").set("axisorientation", true);
    model.result().export("img2").set("logo3d", true);
    model.result().export("img2").set("size", "current");
    model.result().export("img2").set("unit", "px");
    model.result().export("img2").set("height", "656");
    model.result().export("img2").set("width", "874");
    model.result().export("img2").set("lockratio", "off");
    model.result().export("img2").set("resolution", "500");
    model.result().export("img2").set("antialias", "on");
    model.result().export("img2").set("zoomextents", "off");
    model.result().export("img2").set("fontsize", "9");
    model.result().export("img2").set("colortheme", "globaltheme");
    model.result().export("img2").set("customcolor", new double[]{1, 1, 1});
    model.result().export("img2").set("background", "color");
    model.result().export("img2").set("gltfincludelines", "on");
    model.result().export("img2").set("title1d", "on");
    model.result().export("img2").set("legend1d", "on");
    model.result().export("img2").set("logo1d", "on");
    model.result().export("img2").set("options1d", "on");
    model.result().export("img2").set("title2d", "off");
    model.result().export("img2").set("legend2d", "off");
    model.result().export("img2").set("logo2d", "on");
    model.result().export("img2").set("options2d", "on");
    model.result().export("img2").set("title3d", "on");
    model.result().export("img2").set("legend3d", "on");
    model.result().export("img2").set("logo3d", "on");
    model.result().export("img2").set("options3d", "on");
    model.result().export("img2").set("axisorientation", "on");
    model.result().export("img2").set("grid", "on");
    model.result().export("img2").set("axes1d", "on");
    model.result().export("img2").set("axes2d", "off");
    model.result().export("img2").set("showgrid", "on");
    model.result().export("img2").set("target", "file");
    model.result().export("img2").set("qualitylevel", "100");
    model.result().export("img2").set("qualityactive", "on");
    model.result().export("img2").set("imagetype", "png");
    model.result().export("img2").set("lockview", "off");
    model.result().export("img1").set("size", "current");
    model.result().export("img1").set("unit", "px");
    model.result().export("img1").set("height", "656");
    model.result().export("img1").set("width", "874");
    model.result().export("img1").set("lockratio", "off");
    model.result().export("img1").set("resolution", "500");
    model.result().export("img1").set("antialias", "on");
    model.result().export("img1").set("zoomextents", "off");
    model.result().export("img1").set("fontsize", "9");
    model.result().export("img1").set("colortheme", "globaltheme");
    model.result().export("img1").set("customcolor", new double[]{1, 1, 1});
    model.result().export("img1").set("background", "color");
    model.result().export("img1").set("gltfincludelines", "on");
    model.result().export("img1").set("title1d", "on");
    model.result().export("img1").set("legend1d", "on");
    model.result().export("img1").set("logo1d", "on");
    model.result().export("img1").set("options1d", "on");
    model.result().export("img1").set("title2d", "on");
    model.result().export("img1").set("legend2d", "on");
    model.result().export("img1").set("logo2d", "on");
    model.result().export("img1").set("options2d", "on");
    model.result().export("img1").set("title3d", "off");
    model.result().export("img1").set("legend3d", "on");
    model.result().export("img1").set("logo3d", "on");
    model.result().export("img1").set("options3d", "on");
    model.result().export("img1").set("axisorientation", "off");
    model.result().export("img1").set("grid", "off");
    model.result().export("img1").set("axes1d", "on");
    model.result().export("img1").set("axes2d", "on");
    model.result().export("img1").set("showgrid", "on");
    model.result().export("img1").set("target", "file");
    model.result().export("img1").set("qualitylevel", "100");
    model.result().export("img1").set("qualityactive", "on");
    model.result().export("img1").set("imagetype", "png");
    model.result().export("img1").set("lockview", "off");
    model.result().export("img2").set("size", "current");
    model.result().export("img2").set("unit", "px");
    model.result().export("img2").set("height", "656");
    model.result().export("img2").set("width", "874");
    model.result().export("img2").set("lockratio", "off");
    model.result().export("img2").set("resolution", "500");
    model.result().export("img2").set("antialias", "on");
    model.result().export("img2").set("zoomextents", "off");
    model.result().export("img2").set("fontsize", "9");
    model.result().export("img2").set("colortheme", "globaltheme");
    model.result().export("img2").set("customcolor", new double[]{1, 1, 1});
    model.result().export("img2").set("background", "color");
    model.result().export("img2").set("gltfincludelines", "on");
    model.result().export("img2").set("title1d", "on");
    model.result().export("img2").set("legend1d", "on");
    model.result().export("img2").set("logo1d", "on");
    model.result().export("img2").set("options1d", "on");
    model.result().export("img2").set("title2d", "off");
    model.result().export("img2").set("legend2d", "off");
    model.result().export("img2").set("logo2d", "on");
    model.result().export("img2").set("options2d", "on");
    model.result().export("img2").set("title3d", "on");
    model.result().export("img2").set("legend3d", "on");
    model.result().export("img2").set("logo3d", "on");
    model.result().export("img2").set("options3d", "on");
    model.result().export("img2").set("axisorientation", "on");
    model.result().export("img2").set("grid", "on");
    model.result().export("img2").set("axes1d", "on");
    model.result().export("img2").set("axes2d", "off");
    model.result().export("img2").set("showgrid", "on");
    model.result().export("img2").set("target", "file");

    return model;
  }

  public static Model run2(Model model) {
    model.result().export("img2").set("qualitylevel", "100");
    model.result().export("img2").set("qualityactive", "on");
    model.result().export("img2").set("imagetype", "png");
    model.result().export("img2").set("lockview", "off");
    model.result().export("img1").set("size", "current");
    model.result().export("img1").set("unit", "px");
    model.result().export("img1").set("height", "656");
    model.result().export("img1").set("width", "874");
    model.result().export("img1").set("lockratio", "off");
    model.result().export("img1").set("resolution", "500");
    model.result().export("img1").set("antialias", "on");
    model.result().export("img1").set("zoomextents", "off");
    model.result().export("img1").set("fontsize", "9");
    model.result().export("img1").set("colortheme", "globaltheme");
    model.result().export("img1").set("customcolor", new double[]{1, 1, 1});
    model.result().export("img1").set("background", "color");
    model.result().export("img1").set("gltfincludelines", "on");
    model.result().export("img1").set("title1d", "on");
    model.result().export("img1").set("legend1d", "on");
    model.result().export("img1").set("logo1d", "on");
    model.result().export("img1").set("options1d", "on");
    model.result().export("img1").set("title2d", "on");
    model.result().export("img1").set("legend2d", "on");
    model.result().export("img1").set("logo2d", "on");
    model.result().export("img1").set("options2d", "on");
    model.result().export("img1").set("title3d", "off");
    model.result().export("img1").set("legend3d", "on");
    model.result().export("img1").set("logo3d", "on");
    model.result().export("img1").set("options3d", "on");
    model.result().export("img1").set("axisorientation", "off");
    model.result().export("img1").set("grid", "off");
    model.result().export("img1").set("axes1d", "on");
    model.result().export("img1").set("axes2d", "on");
    model.result().export("img1").set("showgrid", "on");
    model.result().export("img1").set("target", "file");
    model.result().export("img1").set("qualitylevel", "100");
    model.result().export("img1").set("qualityactive", "on");
    model.result().export("img1").set("imagetype", "png");
    model.result().export("img1").set("lockview", "off");
    model.result().export("img2").set("size", "current");
    model.result().export("img2").set("unit", "px");
    model.result().export("img2").set("height", "656");
    model.result().export("img2").set("width", "874");
    model.result().export("img2").set("lockratio", "off");
    model.result().export("img2").set("resolution", "500");
    model.result().export("img2").set("antialias", "on");
    model.result().export("img2").set("zoomextents", "off");
    model.result().export("img2").set("fontsize", "9");
    model.result().export("img2").set("colortheme", "globaltheme");
    model.result().export("img2").set("customcolor", new double[]{1, 1, 1});
    model.result().export("img2").set("background", "color");
    model.result().export("img2").set("gltfincludelines", "on");
    model.result().export("img2").set("title1d", "on");
    model.result().export("img2").set("legend1d", "on");
    model.result().export("img2").set("logo1d", "on");
    model.result().export("img2").set("options1d", "on");
    model.result().export("img2").set("title2d", "off");
    model.result().export("img2").set("legend2d", "off");
    model.result().export("img2").set("logo2d", "on");
    model.result().export("img2").set("options2d", "on");
    model.result().export("img2").set("title3d", "on");
    model.result().export("img2").set("legend3d", "on");
    model.result().export("img2").set("logo3d", "on");
    model.result().export("img2").set("options3d", "on");
    model.result().export("img2").set("axisorientation", "on");
    model.result().export("img2").set("grid", "on");
    model.result().export("img2").set("axes1d", "on");
    model.result().export("img2").set("axes2d", "off");
    model.result().export("img2").set("showgrid", "on");
    model.result().export("img2").set("target", "file");
    model.result().export("img2").set("qualitylevel", "100");
    model.result().export("img2").set("qualityactive", "on");
    model.result().export("img2").set("imagetype", "png");
    model.result().export("img2").set("lockview", "off");

    return model;
  }

  public static void main(String[] args) {
    Model model = run();
    run2(model);
  }

}

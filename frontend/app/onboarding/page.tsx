/*
  FE-01 /onboarding 页面实现
  3步流程：起名 → 选来源 → 提问
  支持断点续做（localStorage 为准）
*/
import React, { useEffect, useState, useRef } from "react";
import { StepperHorizontal, Button, Card, Input, Select, Option, Grid, Avatar, Tag } from "@mui/material";

const steps = [
  { key: 1, title: "1. 起名", description: "为您的知识空间起个名字", completed: false },
  { key: 2, title: "2. 选来源", description: "选择内容来源", completed: false },
  { key: 3, title: "3. 提问", description: "开始提问试用", completed: false },
];

const engines = ["内置", "Coze", "Dify", "FastGPT"];

export default function OnboardingPage() {
  const [currentStep, setCurrentStep] = useState(1);
  const [spaceName, setSpaceName] = useState(localStorage.getItem("onboarding_space_name") || "");
  const [selectedEngine, setSelectedEngine] = useState("");
  const [selectedSource, setSelectedSource] = useState("");
  const [question, setQuestion] = useState("");
  const formRef = useRef<HTMLFormElement>(null);

  // 断点续做：读取 localStorage
  useEffect(() => {
    const stored = localStorage.getItem("onboarding_step");
    if (stored) {
      setCurrentStep(parseInt(stored, 10));
    }
  }, []);

  useEffect(() => {
    localStorage.setItem("onboarding_step", currentStep.toString());
  }, [currentStep]);

  const nextStep = () => {
    if (currentStep < 3) {
      setCurrentStep(currentStep + 1);
    }
  };

  const prevStep = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (currentStep === 1) {
      // 第1步：保存空间名
      if (!spaceName.trim()) {
        alert("请输入空间名称");
        return;
      }
      localStorage.setItem("onboarding_space_name", spaceName);
      setCurrentStep(2);
    } else if (currentStep === 2) {
      // 第2步：选择来源
      if (!selectedSource) {
        alert("请选择内容来源");
        return;
      }
      localStorage.setItem("onboarding_source", selectedSource);
      setCurrentStep(3);
    } else if (currentStep === 3) {
      // 第3步：提问试用
      if (!question.trim()) {
        alert("请输入问题");
        return;
      }
      // 这里应该跳转到聊天页或触发问答
      alert(`提问提交：${question}`);
      // 重置或完成
      setCurrentStep(1);
    }
  };

  return (
    <div style={{ minHeight: "100vh", padding: "2rem" }}>
      <StepperHorizontal activeStep={currentStep - 1}>
        {steps.map((step) => (
          <StepperStep key={step.key} step={step.key}>
            <StepperLabel
              step={step.key}
              active={step.key <= currentStep}
              completed={step.key <= currentStep}
            >
              {step.title}
            </StepperLabel>
          </StepperStep>
        ))}
      </StepperHorizontal>

      <Card sx={{ p: 3, marginTop: 2, width: "100%", maxWidth: 500 }}>
        {currentStep === 1 && (
          <form onSubmit={handleSubmit} className="space-name-form">
            <h3>创建知识空间</h3>
            <p>请输入您的空间名称（将在主平台 3000 显示）：</p>
            <Input
              placeholder="例如：我的知识库、旅程测试等"
              value={spaceName}
              onChange={(e) => setSpaceName(e.target.value)}
              required
            />
            <Button type="submit" variant="contained" sx={{ mt: 2 }}>
              继续 →
            </Button>
          </form>
        )}

        {currentStep === 2 && (
          <form onSubmit={handleSubmit} className="source-select-form">
            <h3>选择内容来源</h3>
            <p>选择您想要导入的内容类型：</p>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <Button
                  variant="outlined"
                  fullWidth
                  selected={selectedSource === "微信公众号"}
                  onClick={() => setSelectedSource("微信公众号")}
                >
                  微信公众号
                </Button>
              </Grid>
              <Grid item xs={12} sm={6}>
                <Button
                  variant="outlined"
                  fullWidth
                  selected={selectedSource === "链接"}
                  onClick={() => setSelectedSource("链接")}
                >
                  单篇链接
                </Button>
              </Grid>
              <Grid item xs={12} sm={6}>
                <Button
                  variant="outlined"
                  fullWidth
                  selected={selectedSource === "公共库"}
                  onClick={() => setSelectedSource("公共库")}
                >
                  公共库
                </Button>
              </Grid>
            </Grid>
            <Button type="submit" variant="contained" sx={{ mt: 2 }}>
              继续 →
            </Button>
          </form>
        )}

        {currentStep === 3 && (
          <form onSubmit={handleSubmit} className="question-form">
            <h3>提问试用</h3>
            <p>输入一个问题，体验知识库问答功能：</p>
            <Input
              placeholder="例如：GPT-4 的主要特性有哪些？"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              required
            />
            <Button type="submit" variant="contained" sx={{ mt: 2 }}>
              提交
            </Button>
            <Button
              variant="outlined"
              sx={{ mx: 1 }}
              onClick={() => setCurrentStep(1)}
            >
              重新开始
            </Button>
          </form>
        )}
      </Card>

      {/* 刷新断点续做横幅 */}
      {currentStep === 1 && (
        <div style={{ marginTop: 1, background: "#fcf8e3", padding: "0.5rem", borderRadius: 4, border: "1px solid #e6c93e" }}>
          <span>
            上次进行到第 {localStorage.getItem("onboarding_step") || 1} 步，刷新将继续上次进度
          </span>
        </div>
      )}
    </div>
  );
}

// Stepper 组件辅助
function StepperStep({ step, children, ...props }: any) {
  return <div {...props}>{children}</div>;
}

function StepperLabel({ step, active, completed, children, ...props }: any) {
  const size = active || completed ? 24 : 16;
  const bg = active || completed ? "#1976d2" : "#ccc";
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill={bg === "#1976d2" ? "none" : "currentColor"}
      style={{ borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center" }}
    >
      <text
        x={size / 2}
        y={size / 2}
        fill={bg === "#1976d2" ? "white" : "black"}
        fontSize={size * 0.4}
      >
        {step}
      </text>
    </svg>
  );
}

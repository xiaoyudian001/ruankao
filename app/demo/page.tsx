import type {Metadata} from 'next';
import DemoWorkspace from './demo-workspace';

export const metadata:Metadata={
  title:'公开演示 · 软考 AI 学习助手',
  description:'无需登录，体验有来源的问答、案例逐问练习和论文修改点评。使用自写资料与预录结果，电脑离线也可查看。',
};

export default function DemoPage(){return <DemoWorkspace/>;}

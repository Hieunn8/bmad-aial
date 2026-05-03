import { createFileRoute } from '@tanstack/react-router';

import { Epic5BWorkspace } from '../components/epic5b/Epic5BWorkspace';

export const Route = createFileRoute('/')({
  component: IndexPage,
});

function IndexPage(): React.JSX.Element {
  return <Epic5BWorkspace />;
}

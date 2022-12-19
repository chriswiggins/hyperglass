import { useMemo } from 'react';
import { Wrap, VStack, Flex, chakra } from '@chakra-ui/react';
import { useFormContext } from 'react-hook-form';
import { Select, LocationCard } from '~/components';
import { useConfig } from '~/context';
import { useFormState } from '~/hooks';
import { isMultiValue, isSingleValue } from '~/components/select';

import type { DeviceGroup, SingleOption, OptionGroup, FormData, OnChangeArgs } from '~/types';
import type { SelectOnChange } from '~/components/select';

/** Location option type alias for future extensions. */
export type LocationOption = SingleOption;

interface QueryLocationProps {
  onChange: (f: OnChangeArgs) => void;
  label: string;
}

function buildOptions(devices: DeviceGroup[]): OptionGroup<LocationOption>[] {
  return devices
    .map(group => {
      const label = group.group;
      const options = group.locations
        .map(
          loc =>
            ({
              label: loc.name,
              value: loc.id,
              group: loc.group,
              data: {
                avatar: loc.avatar,
                description: loc.description,
              },
            } as SingleOption),
        )
        .sort((a, b) => (a.label < b.label ? -1 : a.label > b.label ? 1 : 0));
      return { label, options };
    })
    .sort((a, b) => (a.label < b.label ? -1 : a.label > b.label ? 1 : 0));
}

export const QueryLocation = (props: QueryLocationProps): JSX.Element => {
  const { onChange, label } = props;

  const {
    devices,
    web: { locationDisplayMode },
  } = useConfig();
  const {
    formState: { errors },
  } = useFormContext<FormData>();
  const selections = useFormState(s => s.selections);
  const setSelection = useFormState(s => s.setSelection);
  const { form, filtered } = useFormState(({ form, filtered }) => ({ form, filtered }));
  const options = useMemo(() => buildOptions(devices), [devices]);

  const element = useMemo(() => {
    if (locationDisplayMode === 'dropdown') {
      return 'select';
    } else if (locationDisplayMode === 'gallery') {
      return 'cards';
    }
    const groups = options.length;
    const maxOptionsPerGroup = Math.max(...options.map(opt => opt.options.length));
    const showCards = groups < 5 && maxOptionsPerGroup < 6;
    return showCards ? 'cards' : 'select';
  }, [options, locationDisplayMode]);

  const noOverlap = useMemo(
    () => form.queryLocation.length > 1 && filtered.types.length === 0,
    [form, filtered],
  );

  /**
   * Update form and state when a card selections change.
   *
   * @param action Add or remove the option.
   * @param option Full option object.
   */
  function handleCardChange(action: 'add' | 'remove', option: SingleOption) {
    const exists = selections.queryLocation.map(q => q.value).includes(option.value);
    if (action === 'add' && !exists) {
      const toAdd = [...form.queryLocation, option.value];
      const newSelections = [...selections.queryLocation, option];
      setSelection('queryLocation', newSelections);
      onChange({ field: 'queryLocation', value: toAdd });
    } else if (action === 'remove' && exists) {
      const index = selections.queryLocation.findIndex(v => v.value === option.value);
      const toRemove = [...form.queryLocation.filter(v => v !== option.value)];
      setSelection(
        'queryLocation',
        selections.queryLocation.filter((_, i) => i !== index),
      );
      onChange({ field: 'queryLocation', value: toRemove });
    }
  }

  /**
   * Update form and state when select element values change.
   *
   * @param options Final value. React-select determines if an option is being added or removed and
   * only sends back the final value.
   */
  const handleSelectChange: SelectOnChange<LocationOption> = (options): void => {
    if (isMultiValue(options)) {
      onChange({ field: 'queryLocation', value: options.map(o => o.value) });
      setSelection<LocationOption>('queryLocation', options);
    } else if (isSingleValue(options)) {
      onChange({ field: 'queryLocation', value: options.value });
      setSelection<LocationOption>('queryLocation', [options]);
    }
  };

  if (element === 'cards') {
    return (
      <Wrap align="flex-start" justify={{ base: 'center', lg: 'space-between' }} shouldWrapChildren>
        {options.map(group => (
          <VStack key={group.label} align="center">
            <chakra.h3 fontSize={{ base: 'sm', md: 'md' }} alignSelf="flex-start" opacity={0.5}>
              {group.label}
            </chakra.h3>
            {group.options.map(opt => {
              return (
                <LocationCard
                  key={opt.label}
                  option={opt}
                  onChange={handleCardChange}
                  hasError={noOverlap}
                  defaultChecked={form.queryLocation.includes(opt.value)}
                />
              );
            })}
          </VStack>
        ))}
      </Wrap>
    );
  } else if (element === 'select') {
    return (
      <Select<LocationOption, true>
        isMulti
        options={options}
        aria-label={label}
        name="queryLocation"
        closeMenuOnSelect={false}
        onChange={handleSelectChange}
        value={selections.queryLocation}
        isError={typeof errors.queryLocation !== 'undefined'}
      />
    );
  }
  return <Flex>No Locations</Flex>;
};